"""
EAF Light — FastAPI 主入口
单进程 All-in-One 三层智能体服务
"""
from __future__ import annotations
import os, sys, logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import core, knowledge, agents, rules, tools

logger = logging.getLogger("eaf")

# ═══════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════

class L0PlanRequest(BaseModel):
    goal: str
    context: dict | None = None

class L1EventRequest(BaseModel):
    domain: str
    event_type: str
    source: str = "external"
    payload: dict = {}
    priority: str = "mid"

class L2TaskRequest(BaseModel):
    user_id: str = "secretary"
    goal: str
    context: dict | None = None
    domain: str = ""

class RuleEvalRequest(BaseModel):
    input_data: dict
    domain: str | None = None
    rule_ids: list[str] | None = None

class KnowledgeRequest(BaseModel):
    agent_type: str = "l2"
    category: str = "fact"  # fact / rule / experience / skill
    content: str
    domain: str = ""
    tags: list[str] | None = None
    confidence: float = 1.0


# ═══════════════════════════════════════════
# FastAPI 应用
# ═══════════════════════════════════════════

def create_app(fleet: dict | None = None) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="EAF Light", version="0.1.0",
                  description="三层智能体架构 — 轻量版")

    # 注入智能体舰队
    if fleet is None:
        fleet = agents.create_agent_fleet()
    app.state.fleet = fleet

    l0: agents.DecisionAgent = fleet["l0"]
    l1_map: dict[str, agents.OperationAgent] = fleet["l1"]
    l2_map: dict[str, agents.PersonalAssistant] = fleet["l2"]
    rule_reg: rules.RuleRegistry = fleet["rule_registry"]
    tool_reg: tools.ToolRegistry = fleet["tool_registry"]
    wm: core.WorldModelProvider = fleet["world_model"]


    # ── 启动事件 ──

    @app.on_event("startup")
    async def startup():
        knowledge.init_db()
        knowledge.audit("system", "eaf", "startup")
        logger.info(f"🚀 EAF Light 就绪")
        logger.info(f"📋 L0: {l0.name}")
        logger.info(f"📋 L1: {len(l1_map)} 个领域")
        logger.info(f"📋 L2: {len(l2_map)} 个助手")
        logger.info(f"📐 规则: {len(rule_reg._rules)} 条")
        logger.info(f"🔧 工具: {len(tool_reg._tools)} 个")
        logger.info(f"🌍 世界模型: {wm.metadata()}")


    # ── L0 战略规划 ──

    @app.post("/api/v1/l0/plan")
    async def l0_plan(req: L0PlanRequest):
        try:
            result = await l0.strategic_planning(req.goal, req.context)
            return {"code": 0, "message": "success", "data": result}
        except Exception as e:
            logger.exception("L0 规划失败")
            raise HTTPException(500, detail=str(e))


    # ── L1 事件处理 ──

    @app.post("/api/v1/l1/event")
    async def l1_event(req: L1EventRequest):
        agent = l1_map.get(req.domain)
        if not agent:
            raise HTTPException(404, detail=f"领域 '{req.domain}' 没有注册 L1 智能体")
        try:
            result = await agent.handle_event(req.model_dump())
            return {"code": 0, "message": "success", "data": result}
        except Exception as e:
            logger.exception(f"L1 [{req.domain}] 处理失败")
            raise HTTPException(500, detail=str(e))


    # ── L2 任务执行 ──

    @app.post("/api/v1/l2/execute")
    async def l2_execute(req: L2TaskRequest):
        pa = l2_map.get(req.user_id)
        if not pa:
            raise HTTPException(404, detail=f"个人助手 '{req.user_id}' 未注册")
        try:
            result = await pa.execute_task({
                "task_id": core.new_id("task"),
                "goal": req.goal,
                "context": req.context or {},
                "domain": req.domain,
            })
            return {"code": 0, "message": "success", "data": result}
        except Exception as e:
            logger.exception(f"L2 [{req.user_id}] 执行失败")
            raise HTTPException(500, detail=str(e))


    # ── 规则评估 ──

    @app.post("/api/v1/rules/evaluate")
    async def rules_evaluate(req: RuleEvalRequest):
        try:
            result = await rule_reg.evaluate_all(req.input_data, req.rule_ids, req.domain)
            return {"code": 0, "message": "success", "data": result}
        except Exception as e:
            raise HTTPException(500, detail=str(e))


    @app.get("/api/v1/rules")
    async def list_rules(domain: str | None = None):
        return {
            "code": 0,
            "data": [
                {"rule_id": r.rule_id, "name": r.name, "domain": r.domain,
                 "severity": r.severity, "type": r.rule_type}
                for r in rule_reg.list(domain)
            ],
        }


    # ── 智能体状态 ──

    @app.get("/api/v1/agents/status")
    async def agent_status():
        statuses = [l0.to_status()]
        for a in l1_map.values():
            statuses.append(a.to_status())
        for a in l2_map.values():
            statuses.append(a.to_status())
        return {"code": 0, "data": statuses}


    @app.get("/api/v1/agents/l1")
    async def list_l1_agents():
        return {
            "code": 0,
            "data": [
                {"agent_id": a.agent_id, "name": a.name, "domain": a.domain,
                 "status": a.status, "task_count": a.task_count}
                for a in l1_map.values()
            ],
        }


    @app.get("/api/v1/agents/l2")
    async def list_l2_agents():
        return {
            "code": 0,
            "data": [
                {"agent_id": a.agent_id, "name": a.name, "role": a.role,
                 "status": a.status, "task_count": a.task_count}
                for a in l2_map.values()
            ],
        }


    # ── 工具 ──

    @app.get("/api/v1/tools")
    async def list_tools():
        return {"code": 0, "data": tool_reg.list()}


    @app.post("/api/v1/tools/{tool_id}/execute")
    async def execute_tool(tool_id: str, params: dict = {}):
        tool = tool_reg.get(tool_id)
        if not tool:
            raise HTTPException(404, detail=f"工具 '{tool_id}' 未注册")
        result = await tool.execute(params)
        return {"code": 0, "data": result}


    # ── 知识 ──

    @app.post("/api/v1/knowledge")
    async def add_knowledge(req: KnowledgeRequest):
        item_id = knowledge.add_knowledge(
            req.agent_type, req.category, req.content,
            req.domain, req.tags, req.confidence,
        )
        return {"code": 0, "data": {"item_id": item_id}}


    @app.get("/api/v1/knowledge")
    async def query_knowledge(
        agent_type: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ):
        items = knowledge.query_knowledge(agent_type, domain, category, limit)
        return {"code": 0, "data": items}


    # ── 事件日志 ──

    @app.get("/api/v1/events")
    async def list_events(domain: str | None = None, limit: int = 50):
        items = knowledge.list_events(domain, limit)
        return {"code": 0, "data": items}


    # ── 审计 ──

    @app.get("/api/v1/audit")
    async def list_audit(limit: int = 50):
        return {"code": 0, "data": knowledge.list_audit(limit)}


    # ── 世界模型 ──

    @app.get("/api/v1/world-model")
    async def world_model():
        return {"code": 0, "data": wm.metadata()}


    # ── 健康检查 ──

    @app.get("/health")
    async def health():
        return {"status": "ok", "agents": len(l1_map) + len(l2_map) + 1, "rules": len(rule_reg._rules)}

    return app


# ═══════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("EAF_PORT", 6010))
    uvicorn.run("agent_light.main:app", host="0.0.0.0", port=port, reload=True)
