"""
EAF Light — 规则引擎
数值规则 + LLM 语义规则双引擎
"""
from __future__ import annotations
import json, os, inspect, re
import logging
from typing import Any, Callable

logger = logging.getLogger("eaf.rules")

# ═══════════════════════════════════════════
# LLM 客户端（按需导入）
# ═══════════════════════════════════════════

_llm_client = None

def _get_llm():
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    api_key = os.environ.get("EAF_LLM_API_KEY")
    base_url = os.environ.get("EAF_LLM_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("EAF_LLM_MODEL", "deepseek-chat")
    if not api_key:
        logger.warning("EAF_LLM_API_KEY 未设置，语义规则将降级")
        return None
    try:
        from openai import OpenAI
        _llm_client = OpenAI(api_key=api_key, base_url=base_url)
        _llm_client._eaf_model = model
        return _llm_client
    except ImportError:
        logger.warning("openai 包未安装，语义规则将降级")
        return None


# ═══════════════════════════════════════════
# 规则定义
# ═══════════════════════════════════════════

class RuleDefinition:
    """规则定义 — 支持数值规则（同步）和语义规则（异步 LLM）"""
    def __init__(self, rule_id: str, name: str, domain: str = "",
                 severity: str = "mid", rule_type: str = "numeric",
                 evaluate_fn: Callable | None = None,
                 condition: dict | None = None,
                 prompt_template: str | None = None,
                 output: dict | None = None):
        self.rule_id = rule_id
        self.name = name
        self.domain = domain
        self.severity = severity
        self.rule_type = rule_type
        self.evaluate_fn = evaluate_fn
        self.condition = condition or {}
        self.prompt_template = prompt_template
        self.output = output or {"risk_level": "low", "score": 0.0, "trigger_behavior": ""}

    async def evaluate(self, input_data: dict) -> tuple[bool, float, str, str]:
        """
        执行规则判定。
        返回: (matched, score, risk_level, trigger_behavior)
        """
        if self.rule_type == "numeric" and self.evaluate_fn:
            result = self.evaluate_fn(input_data)
            if inspect.iscoroutine(result):
                return await result
            return result

        if self.rule_type == "semantic":
            return await self._evaluate_semantic(input_data)

        # 基于 condition dict 的通用数值判定
        return self._evaluate_condition(input_data)

    def _evaluate_condition(self, input_data: dict) -> tuple[bool, float, str, str]:
        """基于 condition dict 的通用判定"""
        field = self.condition.get("field", "")
        op = self.condition.get("operator", "gt")
        threshold = self.condition.get("threshold", 0)

        value = input_data.get(field)
        if value is None:
            return (False, 0.0, "low", "")

        # 字符串操作（eq, in）直接比较字符串，不转 float
        if op in ("eq", "in"):
            str_value = str(value)
            if op == "eq":
                matched = str_value == str(threshold)
                score = 100 if matched else 0
            else:
                targets = [str(t) for t in (threshold if isinstance(threshold, list) else [threshold])]
                matched = str_value in targets
                score = 80 if matched else 0
            if matched:
                return (True, score, self.output.get("risk_level", "high"),
                        self.output.get("trigger_behavior", ""))
            return (False, 0.0, "low", "")

        # 数值操作（gt, gte, lt）转 float
        try:
            num_value = float(value)
            num_threshold = float(threshold)
        except (ValueError, TypeError):
            return (False, 0.0, "low", "")

        matched = False
        score = 0.0

        if op == "gt" and num_value > num_threshold:
            matched = True
            score = min(100, (num_value / max(num_threshold, 1)) * 50)
        elif op == "gte" and num_value >= num_threshold:
            matched = True
            score = min(100, (num_value / max(num_threshold, 1)) * 50)
        elif op == "lt" and num_value < num_threshold:
            matched = True
            score = min(100, (num_threshold / max(num_value, 1)) * 30)

        if matched:
            return (True, score, self.output.get("risk_level", "high"),
                    self.output.get("trigger_behavior", ""))
        return (False, 0.0, "low", "")

    async def _evaluate_semantic(self, input_data: dict) -> tuple[bool, float, str, str]:
        """LLM 语义规则判定"""
        llm = _get_llm()
        if not llm:
            logger.warning(f"[{self.rule_id}] LLM 不可用，语义规则降级为未命中")
            return (False, 0.0, "low", "")

        prompt = self.prompt_template or ""
        # 填充模板
        for k, v in input_data.items():
            placeholder = "{" + k + "}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(v))

        try:
            resp = llm.chat.completions.create(
                model=getattr(llm, "_eaf_model", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": f"你是企业业务规则专家。请根据以下规则 '{self.name}' 判定输入数据。返回 JSON：{{\"matched\": true/false, \"score\": 0-100, \"reason\": \"...\"}}"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
            # 清理 markdown 包裹
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
            result = json.loads(text)
            if result.get("matched"):
                score = min(100, float(result.get("score", 80)))
                return (True, score, self.output.get("risk_level", "high"),
                        self.output.get("trigger_behavior", ""))
        except Exception as e:
            logger.error(f"[{self.rule_id}] 语义规则 LLM 调用失败: {e}")
        return (False, 0.0, "low", "")


# ═══════════════════════════════════════════
# 规则注册表
# ═══════════════════════════════════════════

class RuleRegistry:
    """规则注册表"""
    def __init__(self):
        self._rules: dict[str, RuleDefinition] = {}

    def register(self, rule: RuleDefinition):
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> RuleDefinition | None:
        return self._rules.get(rule_id)

    def list(self, domain: str | None = None,
             severity: str | None = None) -> list[RuleDefinition]:
        results = list(self._rules.values())
        if domain:
            results = [r for r in results if r.domain == domain]
        if severity:
            results = [r for r in results if r.severity == severity]
        return results

    async def evaluate_all(self, input_data: dict,
                           rule_ids: list[str] | None = None,
                           domain: str | None = None) -> dict:
        """批量规则评估，返回聚合结果"""
        rules = self.list(domain=domain)
        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]

        if not rules:
            return {
                "matched": False, "risk_level": "low", "risk_score": 0.0,
                "trigger_behaviors": [], "details": [],
            }

        results = []
        for rule in rules:
            matched, score, risk_level, behavior = await rule.evaluate(input_data)
            results.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "matched": matched,
                "score": score,
                "risk_level": risk_level,
                "trigger_behavior": behavior,
            })

        # 聚合：最高风险级别 + 平均分
        all_matched = [r for r in results if r["matched"]]
        if not all_matched:
            return {
                "matched": False, "risk_level": "low", "risk_score": 0.0,
                "trigger_behaviors": [], "details": results,
            }

        level_order = {"low": 0, "mid": 1, "high": 2, "critical": 3}
        worst = max(all_matched, key=lambda r: level_order.get(r["risk_level"], 0))
        avg_score = sum(r["score"] for r in all_matched) / len(all_matched)
        behaviors = list(set(r["trigger_behavior"] for r in all_matched if r["trigger_behavior"]))

        return {
            "matched": True,
            "risk_level": worst["risk_level"],
            "risk_score": round(avg_score, 1),
            "trigger_behaviors": behaviors,
            "details": results,
        }


# ═══════════════════════════════════════════
# 领域规则注册函数
# ═══════════════════════════════════════════

def register_domain_rules(registry: RuleRegistry):
    """注册所有预定义领域规则"""

    # ── 采购领域 ──
    registry.register(RuleDefinition(
        rule_id="R-PROC-001",
        name="采购金额超限审查",
        domain="procurement",
        severity="high",
        rule_type="numeric",
        condition={"field": "amount", "operator": "gt", "threshold": 3000000},
        output={"risk_level": "high", "score": 85, "trigger_behavior": "B-PROC-001"},
    ))
    registry.register(RuleDefinition(
        rule_id="R-PROC-002",
        name="新供应商高风险",
        domain="procurement",
        severity="high",
        rule_type="numeric",
        condition={"field": "supplier_age_days", "operator": "lt", "threshold": 180},
        output={"risk_level": "high", "score": 75, "trigger_behavior": "B-PROC-002"},
    ))
    registry.register(RuleDefinition(
        rule_id="R-PROC-003",
        name="供应商关系异常（语义）",
        domain="procurement",
        severity="critical",
        rule_type="semantic",
        prompt_template=(
            "请判断以下采购合同是否存在供应商关联关系异常风险：\n"
            "合同金额：{amount}元\n"
            "供应商名称：{supplier_name}\n"
            "供应商成立时间：{supplier_age_days}天前\n"
            "供应商法人：{supplier_legal_person}\n"
            "采购物品：{item}\n"
            "关联迹象：{suspicious_signs}\n"
            "请输出 JSON 格式判断结果。"
        ),
        output={"risk_level": "critical", "score": 90, "trigger_behavior": "B-PROC-003"},
    ))

    # ── 财务领域 ──
    registry.register(RuleDefinition(
        rule_id="R-FIN-001",
        name="付款金额超限审查",
        domain="finance",
        severity="high",
        rule_type="numeric",
        condition={"field": "amount", "operator": "gt", "threshold": 500000},
        output={"risk_level": "high", "score": 80, "trigger_behavior": "B-FIN-001"},
    ))
    registry.register(RuleDefinition(
        rule_id="R-FIN-002",
        name="三单匹配异常",
        domain="finance",
        severity="critical",
        rule_type="numeric",
        condition={"field": "mismatch_count", "operator": "gt", "threshold": 0},
        output={"risk_level": "critical", "score": 95, "trigger_behavior": "B-FIN-002"},
    ))

    # ── 合同审核领域 ──
    registry.register(RuleDefinition(
        rule_id="R-CON-001",
        name="合同到期提醒",
        domain="contract_review",
        severity="mid",
        rule_type="numeric",
        condition={"field": "days_to_expiry", "operator": "lt", "threshold": 30},
        output={"risk_level": "mid", "score": 60, "trigger_behavior": "B-CON-001"},
    ))

    logger.info(f"已注册 {len(registry._rules)} 条领域规则")


# 全局规则注册表
registry = RuleRegistry()
