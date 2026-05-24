"""
EAF Light — 端到端测试
覆盖三层智能体核心流程
"""
import os, sys, json, pytest, tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_light import core, knowledge, rules, tools, agents


# ═══════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def fleet():
    """创建完整的智能体舰队"""
    knowledge.DB_PATH = tempfile.mktemp(suffix=".db")
    knowledge.init_db()
    return agents.create_agent_fleet()


# ═══════════════════════════════════════════
# 1. 核心类型测试
# ═══════════════════════════════════════════

class TestCoreTypes:
    def test_event_def(self):
        e = core.EventDef(event_type="test.event", name="测试事件", domain="procurement")
        assert e.event_type == "test.event"
        assert e.priority == "mid"
        assert e.domain == "procurement"

    def test_flow_def_with_steps(self):
        f = core.FlowDef(
            flow_id="flow-test",
            name="测试流程",
            steps=[
                core.FlowStep(step_id="s1", name="步骤1"),
                core.FlowStep(step_id="s2", name="步骤2"),
            ],
        )
        assert len(f.steps) == 2

    def test_world_model_metadata(self):
        wm = core.WorldModelProvider()
        meta = wm.metadata()
        assert meta["name"] == "EAF Light WorldModel"
        assert meta["events"] == 0
        assert meta["rules"] == 0

    def test_event_in_event_out(self):
        evt = core.EventIn(event_type="test", source="system", payload={"k": "v"})
        out = core.EventOut(event_id="evt-1", status="accepted")
        assert out.status == "accepted"

    def test_new_id_format(self):
        id1 = core.new_id("test")
        assert id1.startswith("test-")
        assert len(id1) == 17

    def test_utc_now(self):
        now = core.utc_now()
        assert "T" in now


# ═══════════════════════════════════════════
# 2. WorldModelProvider 测试
# ═══════════════════════════════════════════

class TestWorldModelProvider:
    def test_empty_provider(self):
        wm = core.WorldModelProvider()
        assert wm.get_event_def("nonexistent") is None
        assert wm.get_flow_def("nonexistent") is None
        assert wm.list_events() == []
        assert wm.list_rules() == []


# ═══════════════════════════════════════════
# 3. 知识存储测试
# ═══════════════════════════════════════════

class TestKnowledge:
    def setup_method(self):
        knowledge.DB_PATH = tempfile.mktemp(suffix=".db")
        knowledge.init_db()

    def test_init_db(self):
        knowledge.init_db()

    def test_save_and_list_events(self):
        knowledge.save_event("evt-1", "procurement.review", "procurement",
                             "system", {"amount": 5000000})
        events = knowledge.list_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "procurement.review"
        assert events[0]["payload"]["amount"] == 5000000

    def test_add_and_query_knowledge(self):
        kid = knowledge.add_knowledge("l2", "fact", "钢材采购必须三方比价")
        items = knowledge.query_knowledge(agent_type="l2")
        assert len(items) >= 1
        assert items[0]["content"] == "钢材采购必须三方比价"

    def test_audit_log(self):
        knowledge.audit("trace-1", "eaf", "test", detail={"msg": "hello"})
        logs = knowledge.list_audit()
        assert len(logs) >= 1
        assert logs[0]["operation"] == "test"

    def test_save_plan(self):
        tasks = [{"domain": "procurement", "goal": "评估风险"}]
        knowledge.save_plan("plan-1", "降低采购风险", tasks)
        plans = knowledge.list_plans()
        assert len(plans) == 1
        assert plans[0]["goal"] == "降低采购风险"

    def test_add_edge(self):
        knowledge.add_edge("company-A", "company-B", "transacts_with",
                           "company", "company", {"volume": 5000000})
        edges = knowledge.query_graph(source_id="company-A")
        assert len(edges) >= 1
        assert edges[0]["relation"] == "transacts_with"


# ═══════════════════════════════════════════
# 4. 规则引擎测试
# ═══════════════════════════════════════════

class TestRuleEngine:
    def test_numeric_rule_gt(self):
        reg = rules.RuleRegistry()
        reg.register(rules.RuleDefinition(
            rule_id="R-001", name="金额超限",
            condition={"field": "amount", "operator": "gt", "threshold": 100},
            output={"risk_level": "high", "score": 80, "trigger_behavior": "B-001"},
        ))
        matched, score, rl, behavior = reg._rules["R-001"]._evaluate_condition({"amount": 200})
        assert matched is True
        assert score > 0

        matched, score, rl, behavior = reg._rules["R-001"]._evaluate_condition({"amount": 50})
        assert matched is False

    @pytest.mark.asyncio
    async def test_evaluate_all_basic(self):
        reg = rules.RuleRegistry()
        reg.register(rules.RuleDefinition(
            rule_id="R-001", name="金额超限",
            condition={"field": "amount", "operator": "gt", "threshold": 100},
            output={"risk_level": "high", "score": 80, "trigger_behavior": "B-001"},
        ))
        result = await reg.evaluate_all({"amount": 200})
        assert result["matched"] is True
        assert result["risk_level"] == "high"
        assert "B-001" in result["trigger_behaviors"]

    @pytest.mark.asyncio
    async def test_evaluate_all_no_match(self):
        reg = rules.RuleRegistry()
        reg.register(rules.RuleDefinition(
            rule_id="R-001", name="金额超限",
            condition={"field": "amount", "operator": "gt", "threshold": 100},
            output={"risk_level": "high", "score": 80, "trigger_behavior": "B-001"},
        ))
        result = await reg.evaluate_all({"amount": 50})
        assert result["matched"] is False
        assert result["risk_level"] == "low"
        assert result["trigger_behaviors"] == []

    def test_register_domain_rules(self):
        reg = rules.RuleRegistry()
        rules.register_domain_rules(reg)
        assert len(reg.list()) >= 5

    def test_domain_filter(self):
        reg = rules.RuleRegistry()
        rules.register_domain_rules(reg)
        procurement_rules = reg.list(domain="procurement")
        finance_rules = reg.list(domain="finance")
        assert len(procurement_rules) >= 1
        assert len(finance_rules) >= 1

    @pytest.mark.asyncio
    async def test_domain_scoped_eval(self):
        reg = rules.RuleRegistry()
        rules.register_domain_rules(reg)
        result = await reg.evaluate_all(
            {"amount": 5000000, "supplier_age_days": 30},
            domain="procurement",
        )
        assert result["matched"] is True

    @pytest.mark.asyncio
    async def test_multi_rule_aggregation(self):
        reg = rules.RuleRegistry()
        reg.register(rules.RuleDefinition(
            rule_id="R-A", name="规则A", severity="high",
            condition={"field": "x", "operator": "gt", "threshold": 10},
            output={"risk_level": "high", "score": 80, "trigger_behavior": "B-A"},
        ))
        reg.register(rules.RuleDefinition(
            rule_id="R-B", name="规则B", severity="critical",
            condition={"field": "y", "operator": "eq", "threshold": "yes"},
            output={"risk_level": "critical", "score": 95, "trigger_behavior": "B-B"},
        ))
        result = await reg.evaluate_all({"x": 20, "y": "yes"})
        assert result["matched"] is True
        assert result["risk_level"] == "critical"
        assert "B-A" in result["trigger_behaviors"]
        assert "B-B" in result["trigger_behaviors"]


# ═══════════════════════════════════════════
# 5. 工具测试
# ═══════════════════════════════════════════

class TestTools:
    def test_register_and_list(self):
        reg = tools.ToolRegistry()
        tools.register_default_tools(reg)
        lst = reg.list()
        assert len(lst) >= 4
        assert any(t["tool_id"] == "tool-notify" for t in lst)

    @pytest.mark.asyncio
    async def test_notify_tool(self):
        reg = tools.ToolRegistry()
        tools.register_default_tools(reg)
        result = await reg.get("tool-notify").execute(
            {"channel": "飞书", "recipients": ["张三"], "message": "测试"}
        )
        assert result["success"] is True
        assert result["output"]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_report_tool(self):
        reg = tools.ToolRegistry()
        tools.register_default_tools(reg)
        result = await reg.get("tool-report").execute(
            {"title": "风险评估报告", "content": "采购合同异常", "type": "approval"}
        )
        assert result["success"] is True
        assert result["output"]["type"] == "approval"

    def test_unknown_tool(self):
        reg = tools.ToolRegistry()
        assert reg.get("nonexistent") is None


# ═══════════════════════════════════════════
# 6. L1 运营智能体测试
# ═══════════════════════════════════════════

class TestL1Agent:
    @pytest.mark.asyncio
    async def test_procurement_high_risk_event(self, fleet):
        l1 = fleet["l1"]["procurement"]
        result = await l1.handle_event({
            "event_type": "procurement.contract_review",
            "source": "system",
            "payload": {
                "amount": 5000000,
                "supplier_name": "新阳光科技",
                "supplier_age_days": 30,
            },
        })
        assert result["status"] == "processed"
        assert result["risk_level"] in ("high", "critical")
        assert result["risk_score"] > 50
        assert len(result["behaviors_executed"]) >= 1

    @pytest.mark.asyncio
    async def test_procurement_low_risk_event(self, fleet):
        l1 = fleet["l1"]["procurement"]
        result = await l1.handle_event({
            "event_type": "procurement.contract_review",
            "source": "system",
            "payload": {
                "amount": 10000,
                "supplier_name": "老供应商科技",
                "supplier_age_days": 500,
            },
        })
        assert result["status"] == "processed"
        assert result["risk_level"] in ("low", "mid")

    @pytest.mark.asyncio
    async def test_finance_mismatch_event(self, fleet):
        l1 = fleet["l1"]["finance"]
        result = await l1.handle_event({
            "event_type": "finance.invoice_check",
            "source": "erp",
            "payload": {"amount": 600000, "mismatch_count": 2},
        })
        assert result["status"] == "processed"
        assert result["risk_level"] == "critical"

    @pytest.mark.asyncio
    async def test_event_persisted(self, fleet):
        db_path = tempfile.mktemp(suffix=".db")
        knowledge.DB_PATH = db_path
        knowledge.init_db()
        l1 = fleet["l1"]["procurement"]
        await l1.handle_event({
            "event_type": "procurement.test_persist",
            "source": "test",
            "payload": {"amount": 1000000},
        })
        events = knowledge.list_events(domain="procurement")
        assert len(events) >= 1


# ═══════════════════════════════════════════
# 7. L0 决策智能体测试
# ═══════════════════════════════════════════

class TestL0Agent:
    @pytest.mark.asyncio
    async def test_strategic_planning_procurement(self, fleet):
        l0 = fleet["l0"]
        result = await l0.strategic_planning("降低采购合同风险")
        assert "plan_id" in result
        assert len(result["tasks"]) >= 1
        domains = [t["domain"] for t in result["tasks"]]
        assert "procurement" in domains  # 至少命中采购领域

    @pytest.mark.asyncio
    async def test_strategic_planning_multi_domain(self, fleet):
        l0 = fleet["l0"]
        result = await l0.strategic_planning("审查财务付款和采购合同")
        domains = [t["domain"] for t in result["tasks"]]
        assert "finance" in domains or "procurement" in domains

    @pytest.mark.asyncio
    async def test_plan_persisted(self, fleet):
        db_path = tempfile.mktemp(suffix=".db")
        knowledge.DB_PATH = db_path
        knowledge.init_db()
        l0 = fleet["l0"]
        result = await l0.strategic_planning("测试规划")
        plans = knowledge.list_plans()
        assert len(plans) >= 1

    def test_agent_status(self, fleet):
        l0 = fleet["l0"]
        status = l0.to_status()
        assert status["agent_type"] == "l0"
        assert status["name"] == "决策智能体"


# ═══════════════════════════════════════════
# 8. L2 个人助手测试
# ═══════════════════════════════════════════

class TestL2Agent:
    @pytest.mark.asyncio
    async def test_execute_notify_task(self, fleet):
        pa = fleet["l2"]["secretary"]
        result = await pa.execute_task({
            "task_id": "task-test",
            "goal": "发送通知给张三，采购合同需要审批",
            "context": {"recipients": ["张三"]},
            "domain": "procurement",
        })
        assert result["status"] == "completed"
        assert result["output"]["tools_called"] >= 1

    @pytest.mark.asyncio
    async def test_execute_report_task(self, fleet):
        pa = fleet["l2"]["secretary"]
        result = await pa.execute_task({
            "task_id": "task-rpt",
            "goal": "生成采购风险评估报告",
            "context": {},
            "domain": "procurement",
        })
        assert result["status"] == "completed"
        tool_names = [t["tool_id"] for t in result["output"]["tool_results"]]
        assert "tool-report" in tool_names

    @pytest.mark.asyncio
    async def test_task_persisted(self, fleet):
        db_path = tempfile.mktemp(suffix=".db")
        knowledge.DB_PATH = db_path
        knowledge.init_db()
        pa = fleet["l2"]["secretary"]
        await pa.execute_task({
            "task_id": "task-persist",
            "goal": "查询钢材采购知识",
            "context": {"topic": "钢材"},
            "domain": "procurement",
        })
        tasks = knowledge.query_knowledge(agent_type="l2")
        assert len(tasks) >= 1


# ═══════════════════════════════════════════
# 9. 端到端工作流测试
# ═══════════════════════════════════════════

class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_l0_to_l1_to_l2_full_flow(self, fleet):
        """完整的 L0 → L1 → L2 链路测试"""
        db_path = tempfile.mktemp(suffix=".db")
        knowledge.DB_PATH = db_path
        knowledge.init_db()

        l0 = fleet["l0"]
        l1 = fleet["l1"]["procurement"]
        pa = fleet["l2"]["secretary"]

        # Step 1: L0 战略规划
        plan = await l0.strategic_planning("评估进口钢材采购风险")
        assert plan["plan_id"]

        # Step 2: L1 处理采购事件
        event_result = await l1.handle_event({
            "event_type": "procurement.steel_contract",
            "source": "purchase_order",
            "payload": {
                "amount": 5000000,
                "supplier_name": "新供应商钢铁",
                "supplier_age_days": 60,
                "item": "进口钢材",
            },
        })
        assert event_result["status"] == "processed"
        assert event_result["risk_level"] in ("high", "critical")

        # Step 3: 如果触发了 L2 任务
        if event_result.get("needs_human_approval"):
            l2_result = await pa.execute_task({
                "goal": "生成审批材料发送通知",
                "context": {
                    "event_id": event_result["event_id"],
                    "risk_level": event_result["risk_level"],
                },
                "domain": "procurement",
            })
            assert l2_result["status"] == "completed"

        # Step 4: 验证审计日志
        audit_logs = knowledge.list_audit()
        assert len(audit_logs) >= 2

    @pytest.mark.asyncio
    async def test_all_agents_ready(self, fleet):
        """验证所有智能体都初始化正确"""
        assert fleet["l0"].agent_id == "l0-decision"
        assert len(fleet["l1"]) == 8
        assert len(fleet["l2"]) == 4
        assert len(fleet["rule_registry"].list()) >= 5
        assert len(fleet["tool_registry"].list()) >= 4
