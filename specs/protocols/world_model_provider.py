"""
Enterprise Agent Framework — World Model Provider Protocol

抽象接口定义：Agent 通过此协议读取和操作世界模型（五要素业务模型）。
E5M Engine 是此协议的参考实现，但协议本身允许任何实现（LLM-Only / 人工标注等）。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════
# 数据对象定义
# ═══════════════════════════════════════════

@dataclass
class EventDef:
    event_type: str
    name: str
    domain: str = ""
    description: str = ""
    trigger_condition: str = ""
    data_sources: list[str] = field(default_factory=list)
    related_rules: list[str] = field(default_factory=list)
    priority: str = "mid"


@dataclass
class FlowStep:
    step_id: str
    name: str
    description: str = ""
    actors: list[str] = field(default_factory=list)
    timeout: int | None = None


@dataclass
class FlowDef:
    flow_id: str
    name: str
    domain: str = ""
    steps: list[FlowStep] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    timeout: int | None = None


@dataclass
class AttributeDef:
    name: str
    type: str
    required: bool = False
    description: str = ""


@dataclass
class RelationshipDef:
    name: str
    target_type: str
    cardinality: str  # 1:1, 1:N, N:M


@dataclass
class ObjectSchema:
    object_type: str
    attributes: list[AttributeDef] = field(default_factory=list)
    state_machine: dict[str, list[str]] = field(default_factory=dict)
    relationships: list[RelationshipDef] = field(default_factory=list)
    related_events: list[str] = field(default_factory=list)


@dataclass
class RuleOutput:
    risk_level: str = "low"  # low / mid / high / critical
    score: float = 0.0
    trigger_behavior: str = ""


@dataclass
class RuleDef:
    rule_id: str
    name: str
    type: str = "numeric"  # numeric / semantic
    description: str = ""
    policy_ref: str | None = None
    condition: dict | None = None
    prompt_template: str | None = None
    output: RuleOutput | None = None


@dataclass
class ActionHandler:
    handler_type: str  # api-executor / rpa-orchestrator / message-sender / event-generator
    config: dict = field(default_factory=dict)


@dataclass
class ApprovalStep:
    role: str
    timeout: int = 3600  # 超时秒数


@dataclass
class ActionDef:
    action_id: str
    name: str
    level: int = 1
    handlers: list[ActionHandler] = field(default_factory=list)
    approval_chain: list[ApprovalStep] = field(default_factory=list)


@dataclass
class EventIn:
    event_type: str
    source: str
    payload: dict
    source_ref: str | None = None
    priority: str = "mid"


@dataclass
class EventOut:
    event_id: str
    event_type: str
    status: str = "accepted"


@dataclass
class ObjectQuery:
    object_type: str
    filters: dict = field(default_factory=dict)
    page: int = 1
    page_size: int = 20


@dataclass
class RuleEvalResult:
    eval_id: str
    matched_rules: list[dict]
    risk_level: str
    risk_score: float
    trigger_actions: list[str]


@dataclass
class ActionResult:
    exec_id: str
    action_id: str
    status: str  # started / completed / failed / awaiting_approval
    output: dict | None = None


@dataclass
class ModelMetadata:
    name: str
    version: str
    description: str = ""


# ═══════════════════════════════════════════
# 抽象协议接口
# ═══════════════════════════════════════════

class WorldModelProvider(ABC):
    """
    世界模型提供者 — 抽象接口

    Enterprise Agent Framework 中的 L0/L1/L2 Agent 通过此接口
    获取和操作业务世界模型。E5M Engine 是此接口的一个实现，
    但可以替换为任何遵循此协议的其他实现。
    """

    # ── 事件 ──

    @abstractmethod
    async def get_event_definition(self, event_type: str) -> EventDef | None:
        """获取事件定义"""
        ...

    @abstractmethod
    async def list_events(self, domain: str | None = None) -> list[EventDef]:
        """获取某领域的所有事件定义"""
        ...

    # ── 流程 ──

    @abstractmethod
    async def get_flow_definition(self, flow_id: str) -> FlowDef | None:
        """获取流程定义"""
        ...

    @abstractmethod
    async def get_flow_steps(self, flow_id: str) -> list[FlowStep]:
        """获取流程的步骤列表"""
        ...

    # ── 对象 ──

    @abstractmethod
    async def get_object_schema(self, object_type: str) -> ObjectSchema | None:
        """获取对象模型定义"""
        ...

    @abstractmethod
    async def query_objects(self, query: ObjectQuery) -> list[dict]:
        """查询业务对象实例"""
        ...

    # ── 规则 ──

    @abstractmethod
    async def get_rule_definitions(
        self, rule_ids: list[str] | None = None
    ) -> list[RuleDef]:
        """获取规则定义"""
        ...

    @abstractmethod
    async def evaluate_rules(
        self, input_data: dict, rule_ids: list[str] | None = None
    ) -> RuleEvalResult:
        """执行规则判定"""
        ...

    # ── 行为 ──

    @abstractmethod
    async def get_action_definition(self, action_id: str) -> ActionDef | None:
        """获取行为定义"""
        ...

    @abstractmethod
    async def execute_action(self, action_id: str, params: dict) -> ActionResult:
        """执行行为"""
        ...

    # ── 事件投递 ──

    @abstractmethod
    async def ingest_event(self, event: EventIn) -> EventOut:
        """向世界模型投递事件"""
        ...

    # ── 图查询 ──

    @abstractmethod
    async def graph_query(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """查询知识图谱"""
        ...

    # ── 元信息 ──

    @abstractmethod
    async def get_model_metadata(self) -> ModelMetadata:
        """获取世界模型的版本信息"""
        ...
