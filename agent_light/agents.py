"""
EAF Light — 三层智能体实现
L0 决策智能体 · L1 运营智能体 · L2 个人助手
"""
from __future__ import annotations
import json, os, re, uuid, asyncio
import logging
from typing import Any

from . import core, knowledge, rules, tools

logger = logging.getLogger("eaf.agents")


# ═══════════════════════════════════════════
# Agent 基类
# ═══════════════════════════════════════════

class AgentBase:
    """智能体基类"""
    def __init__(self, agent_id: str, name: str, agent_type: str):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.status = "idle"  # idle / busy / error
        self.task_count = 0

    def to_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "status": self.status,
            "task_count": self.task_count,
            "last_active": core.utc_now(),
        }


# ═══════════════════════════════════════════
# L0 决策智能体
# ═══════════════════════════════════════════

class DecisionAgent(AgentBase):
    """
    L0 决策智能体
    职责：战略认知 → 目标分解 → L1 编排
    """
    def __init__(self, world_model: core.WorldModelProvider):
        super().__init__("l0-decision", "决策智能体", "l0")
        self.world_model = world_model
        self.l1_agents: dict[str, OperationAgent] = {}
        self.l2_agents: dict[str, PersonalAssistant] = {}

    def register_l1(self, agent: OperationAgent):
        self.l1_agents[agent.domain] = agent

    def register_l2(self, agent: PersonalAssistant):
        self.l2_agents[agent.user_id] = agent

    async def strategic_planning(self, goal: str, context: dict = None) -> dict:
        """
        战略规划：接收一个战略目标，分解为 L1 可执行的任务
        """
        self.status = "busy"
        self.task_count += 1
        plan_id = core.new_id("plan")
        context = context or {}

        logger.info(f"[L0] 战略规划: {goal}")

        # 1. 分析目标 → 确定影响领域
        domains = self._analyze_goal(goal)
        logger.info(f"[L0] 影响领域: {domains}")

        # 2. 分解为子任务
        tasks = self._decompose_goal(goal, domains)

        # 3. 编排到对应 L1
        results = []
        for task in tasks:
            l1 = self.l1_agents.get(task["domain"])
            if l1:
                try:
                    result = await l1.handle_event({
                        "event_type": task.get("event_type", f"{task['domain']}.task"),
                        "source": "l0_decision",
                        "payload": task.get("payload", {}),
                        "priority": task.get("priority", "mid"),
                    })
                    results.append({
                        "task_id": task.get("task_id"),
                        "domain": task["domain"],
                        "status": result.get("status", "processed"),
                        "result": result,
                    })
                except Exception as e:
                    logger.error(f"[L0] L1 任务执行失败 [{task['domain']}]: {e}")
                    results.append({
                        "task_id": task.get("task_id"),
                        "domain": task["domain"],
                        "status": "failed",
                        "error": str(e),
                    })

        # 4. 记录到知识库
        knowledge.save_plan(plan_id, goal, tasks)
        knowledge.add_knowledge("l0", "experience", json.dumps({
            "goal": goal, "tasks": tasks, "results": results,
        }, ensure_ascii=False), domain="strategic")

        self.status = "idle"
        return {
            "plan_id": plan_id,
            "goal": goal,
            "tasks": tasks,
            "results": results,
        }

    def _analyze_goal(self, goal: str) -> list[str]:
        """分析战略目标涉及哪些领域"""
        # 基于关键词的简单匹配
        domain_keywords = {
            "procurement": ["采购", "供应商", "supplier", "purchase", "procurement"],
            "finance": ["财务", "付款", "结算", "报销", "finance", "payment", "invoice"],
            "sales_order": ["销售", "订单", "客户", "sales", "order", "customer"],
            "contract_review": ["合同", "签约", "法务", "contract", "legal"],
            "rd_delivery": ["研发", "交付", "开发", "产品", "rd", "delivery", "development"],
            "lead_capture": ["商机", "线索", "市场", "lead", "opportunity"],
            "hr": ["人力", "招聘", "员工", "hr", "recruit", "onboard"],
            "customer_service": ["客服", "售后", "服务", "service", "support"],
        }
        goal_lower = goal.lower()
        domains = []
        # 使用所有已注册 L1 的领域
        registered = set(self.l1_agents.keys())
        for domain, keywords in domain_keywords.items():
            if domain in registered:
                for kw in keywords:
                    if kw in goal_lower or kw.lower() in goal_lower:
                        domains.append(domain)
                        break
        return domains if domains else ["procurement"]  # 默认采购

    def _decompose_goal(self, goal: str, domains: list[str]) -> list[dict]:
        """将战略目标分解为 L1 任务"""
        tasks = []
        for domain in domains:
            event_type = f"{domain}.strategic_task"
            if domain == "procurement":
                tasks.append({
                    "task_id": core.new_id("task"),
                    "domain": domain,
                    "event_type": event_type,
                    "goal": f"采购风险评估: {goal}",
                    "payload": {"domain": domain, "source_goal": goal},
                    "priority": "high",
                })
            elif domain == "finance":
                tasks.append({
                    "task_id": core.new_id("task"),
                    "domain": domain,
                    "event_type": event_type,
                    "goal": f"财务合规审查: {goal}",
                    "payload": {"domain": domain, "source_goal": goal},
                    "priority": "high",
                })
            else:
                tasks.append({
                    "task_id": core.new_id("task"),
                    "domain": domain,
                    "event_type": event_type,
                    "goal": f"{domain} 相关任务: {goal}",
                    "payload": {"domain": domain, "source_goal": goal},
                    "priority": "mid",
                })
        return tasks


# ═══════════════════════════════════════════
# L1 运营智能体
# ═══════════════════════════════════════════

class OperationAgent(AgentBase):
    """
    L1 运营智能体
    职责：领域事件感知 → 规则判定 → 行为执行
    """
    def __init__(self, domain: str, name: str,
                 world_model: core.WorldModelProvider,
                 rule_registry: rules.RuleRegistry,
                 behavior_defs: dict[str, core.BehaviorDef] | None = None):
        super().__init__(f"l1-{domain}", name, "l1")
        self.domain = domain
        self.world_model = world_model
        self.rule_registry = rule_registry
        self.behavior_defs = behavior_defs or {}

    async def handle_event(self, event: dict) -> dict:
        """
        处理一个领域事件
        event: {event_type, source, payload, priority}
        """
        self.status = "busy"
        self.task_count += 1
        event_id = core.new_id("evt")
        event_type = event.get("event_type", f"{self.domain}.unknown")
        payload = event.get("payload", {})

        logger.info(f"[L1/{self.domain}] 收到事件: {event_type}")

        # 1. 持久化事件
        knowledge.save_event(event_id, event_type, self.domain,
                             event.get("source", ""), payload)

        # 2. 规则判定
        rule_result = await self.rule_registry.evaluate_all(
            input_data=payload,
            domain=self.domain,
        )

        # 3. 记录判定结果
        knowledge.update_event_result(
            event_id,
            rule_result["risk_level"],
            rule_result["risk_score"],
            rule_result["trigger_behaviors"],
        )
        knowledge.audit(event_id, f"l1/{self.domain}", "rule_evaluate",
                        detail={"event_type": event_type, "result": rule_result})

        # 4. 触发行为
        behaviors_executed = []
        for behavior_id in rule_result["trigger_behaviors"]:
            behavior_def = self.behavior_defs.get(behavior_id) or \
                           self.world_model.behaviors.get(behavior_id)
            if behavior_def:
                exec_result = await self._execute_behavior(behavior_def, payload, event_id)
                behaviors_executed.append(exec_result)
            else:
                logger.warning(f"[L1/{self.domain}] 行为未定义: {behavior_id}")

        # 5. 检查是否遇到「人节点」需要调度 L2
        l2_tasks = []
        needs_human = any(b.get("level", 1) >= 3 for b in behaviors_executed
                         if isinstance(b, dict))
        if needs_human:
            l2_tasks.append({
                "type": "approval",
                "reason": f"事件 {event_type} 触发高等级行为",
                "domain": self.domain,
            })

        self.status = "idle"
        return {
            "event_id": event_id,
            "domain": self.domain,
            "risk_level": rule_result["risk_level"],
            "risk_score": rule_result["risk_score"],
            "matched_rules": len([d for d in rule_result.get("details", []) if d.get("matched")]),
            "behaviors_executed": [b.get("behavior_id") for b in behaviors_executed if isinstance(b, dict)],
            "needs_human_approval": needs_human,
            "l2_tasks": l2_tasks,
            "status": "processed",
        }

    async def _execute_behavior(self, behavior: core.BehaviorDef,
                                payload: dict, trace_id: str) -> dict:
        """执行一个行为"""
        logger.info(f"[L1/{self.domain}] 执行行为: {behavior.behavior_id}")

        exec_result = {
            "behavior_id": behavior.behavior_id,
            "name": behavior.name,
            "level": behavior.level,
            "status": "executed",
        }

        # 检查审批链
        if behavior.approval_chain:
            exec_result["approval_required"] = behavior.approval_chain
            exec_result["status"] = "awaiting_approval"

        knowledge.audit(trace_id, f"l1/{self.domain}", f"behavior:{behavior.behavior_id}",
                        detail={"payload_keys": list(payload.keys()), "result": exec_result})

        return exec_result

    def to_status(self) -> dict:
        s = super().to_status()
        s["domain"] = self.domain
        return s


# ═══════════════════════════════════════════
# L2 个人助手
# ═══════════════════════════════════════════

class PersonalAssistant(AgentBase):
    """
    L2 个人助手
    职责：任务执行、知识查询、工具调用
    """
    def __init__(self, user_id: str, name: str, role: str,
                 world_model: core.WorldModelProvider,
                 tool_registry: tools.ToolRegistry):
        super().__init__(f"l2-{user_id}", name, "l2")
        self.user_id = user_id
        self.role = role
        self.world_model = world_model
        self.tool_registry = tool_registry

    async def execute_task(self, task: dict) -> dict:
        """
        执行一个分配的任务
        task: {task_id, goal, context, domain}
        """
        self.status = "busy"
        self.task_count += 1
        task_id = task.get("task_id", core.new_id("task"))
        goal = task.get("goal", "")
        context = task.get("context", {})

        logger.info(f"[L2/{self.role}] 执行任务: {goal[:50]}...")

        # 1. 持久化任务
        knowledge.save_task(task_id, self.agent_id, goal, context)

        # 2. 查询知识库
        relevant_knowledge = knowledge.query_knowledge(
            agent_type="l2", domain=task.get("domain"), limit=5
        )

        # 3. 判断需要调用哪些工具
        tool_calls = []
        goal_lower = goal.lower()

        if any(kw in goal_lower for kw in ["通知", "告知", "发送", "提醒", "notify"]):
            tool_calls.append({
                "tool_id": "tool-notify",
                "params": {
                    "channel": "飞书",
                    "recipients": context.get("recipients", [self.user_id]),
                    "message": goal,
                }
            })
        if any(kw in goal_lower for kw in ["报告", "文档", "报表", "report", "report"]):
            tool_calls.append({
                "tool_id": "tool-report",
                "params": {"title": goal, "content": str(context), "type": "approval"},
            })
        if any(kw in goal_lower for kw in ["知识", "查", "找", "搜索", "know", "search", "find"]):
            tool_calls.append({
                "tool_id": "tool-knowledge",
                "params": {"topic": goal},
            })
        if any(kw in goal_lower for kw in ["会议", "安排", "日程", "meet", "schedule"]):
            tool_calls.append({
                "tool_id": "tool-schedule",
                "params": {"title": goal,
                           "participants": context.get("participants", [self.user_id])},
            })

        # 4. 执行工具
        tool_results = []
        for call in tool_calls:
            tool = self.tool_registry.get(call["tool_id"])
            if tool:
                result = await tool.execute(call["params"])
                tool_results.append({
                    "tool_id": call["tool_id"],
                    "params": call["params"],
                    "result": result,
                })

        # 5. 记录结果
        output = {
            "goal": goal,
            "knowledge_used": len(relevant_knowledge),
            "tools_called": len(tool_results),
            "tool_results": tool_results,
        }
        knowledge.update_task_result(task_id, "completed", output)
        knowledge.add_knowledge("l2", "experience",
                                json.dumps({"task": goal, "tools": tool_calls},
                                           ensure_ascii=False),
                                domain=task.get("domain", ""))

        self.status = "idle"
        return {"task_id": task_id, "status": "completed", "output": output}


# ═══════════════════════════════════════════
# 工厂函数 — 一键创建三层智能体
# ═══════════════════════════════════════════

def create_agent_fleet(config: dict | None = None) -> dict:
    """创建完整的三层智能体舰队"""
    world_model = core.WorldModelProvider()
    rule_registry = rules.registry

    # 注册规则
    rules.register_domain_rules(rule_registry)

    # 注册行为定义（供 L1 规则触发时查找）
    default_behaviors = {
        "B-PROC-001": core.BehaviorDef("B-PROC-001", "采购金额超限审查", "procurement", level=3,
                        approval_chain=[{"role": "采购总监", "timeout": 3600}]),
        "B-PROC-002": core.BehaviorDef("B-PROC-002", "新供应商尽职调查", "procurement", level=2),
        "B-PROC-003": core.BehaviorDef("B-PROC-003", "供应商关系异常阻断", "procurement", level=4,
                        approval_chain=[{"role": "风控总监", "timeout": 7200}, {"role": "董事长", "timeout": 14400}]),
        "B-FIN-001": core.BehaviorDef("B-FIN-001", "付款金额超限审批", "finance", level=3,
                        approval_chain=[{"role": "财务总监", "timeout": 3600}]),
        "B-FIN-002": core.BehaviorDef("B-FIN-002", "三单匹配异常冻结", "finance", level=4),
        "B-CON-001": core.BehaviorDef("B-CON-001", "合同到期提醒", "contract_review", level=1),
    }
    for b_id, b_def in default_behaviors.items():
        world_model.behaviors[b_id] = b_def

    # 注册工具
    tools.register_default_tools(tools.tool_registry)

    # L0 决策智能体
    l0 = DecisionAgent(world_model)

    # L1 运营智能体（8 大领域）
    domain_names = {
        "lead_capture": "商机捕获",
        "sales_order": "销售订单",
        "contract_review": "合同审核",
        "rd_delivery": "研发交付",
        "procurement": "采购管理",
        "finance": "财务结算",
        "hr": "人力资源",
        "customer_service": "客户服务",
    }
    l1_agents = {}
    for domain_id, domain_name in domain_names.items():
        agent = OperationAgent(domain_id, domain_name, world_model, rule_registry)
        l1_agents[domain_id] = agent
        l0.register_l1(agent)

    # L2 个人助手
    l2_assistants = {
        "finance": PersonalAssistant("finance", "财务行政助手", "财务行政", world_model, tools.tool_registry),
        "rd": PersonalAssistant("rd", "产品研发助手", "产品研发", world_model, tools.tool_registry),
        "sales": PersonalAssistant("sales", "售前方案助手", "售前方案", world_model, tools.tool_registry),
        "secretary": PersonalAssistant("secretary", "秘书", "秘书", world_model, tools.tool_registry),
    }
    for pa in l2_assistants.values():
        l0.register_l2(pa)

    return {
        "world_model": world_model,
        "rule_registry": rule_registry,
        "tool_registry": tools.tool_registry,
        "l0": l0,
        "l1": l1_agents,
        "l2": l2_assistants,
    }
