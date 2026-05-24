"""
EAF Light — 核心类型定义
五要素核心数据类型 + WorldModelProvider 轻量实现
"""
from __future__ import annotations
import json, os, yaml
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime, timezone


# ═══════════════════════════════════════════
# 五要素核心数据类型
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
    priority: str = "mid"  # critical / high / mid / low

@dataclass
class FlowStep:
    step_id: str
    name: str
    description: str = ""
    actor: str = "system"  # system / l1_agent / l2_agent / human
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
    type: str = "string"  # string / number / boolean / date / ref
    required: bool = False
    description: str = ""

@dataclass
class RelationshipDef:
    name: str
    target_type: str
    cardinality: str = "1:N"  # 1:1 / 1:N / N:M

@dataclass
class ObjectSchema:
    object_type: str
    attributes: list[AttributeDef] = field(default_factory=list)
    state_machine: dict[str, list[str]] = field(default_factory=dict)
    relationships: list[RelationshipDef] = field(default_factory=list)
    related_events: list[str] = field(default_factory=list)

@dataclass
class RuleDef:
    rule_id: str
    name: str
    type: str = "numeric"  # numeric / semantic
    description: str = ""
    domain: str = ""
    severity: str = "mid"  # critical / high / mid / low
    condition: dict | None = None       # 数值规则条件
    prompt_template: str | None = None  # 语义规则 Prompt
    output: dict | None = None          # {risk_level, score, trigger_behavior}

@dataclass
class ActionDef:
    action_id: str
    name: str
    description: str = ""
    level: int = 1   # 1-4
    handlers: list[dict] = field(default_factory=list)

@dataclass
class BehaviorDef:
    """行为定义（L1 的原子操作）"""
    behavior_id: str
    name: str
    domain: str = ""
    level: int = 1
    preconditions: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    approval_chain: list[dict] = field(default_factory=list)  # [{"role": "...", "timeout": 3600}]

# ═══════════════════════════════════════════
# 运行时消息类型
# ═══════════════════════════════════════════

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
    status: str = "accepted"  # accepted / processed / failed
    result: dict | None = None

@dataclass
class Task:
    """L0 → L1 / L1 → L2 的任务描述"""
    task_id: str
    domain: str
    goal: str
    context: dict = field(default_factory=dict)
    priority: str = "mid"
    status: str = "pending"  # pending / running / completed / failed
    output: dict | None = None
    created_at: str = ""

@dataclass
class AgentStatus:
    agent_id: str
    agent_type: str  # l0 / l1 / l2
    name: str
    status: str  # idle / busy / error
    task_count: int = 0
    domains: list[str] = field(default_factory=list)
    last_active: str = ""

# ═══════════════════════════════════════════
# WorldModelProvider — 轻量内存实现
# ═══════════════════════════════════════════

class WorldModelProvider:
    """
    轻量级世界模型提供者。
    所有数据存储在内存中（启动时从 YAML/MD 文件加载），
    同时持久化到 SQLite。
    """
    def __init__(self):
        self.events: dict[str, EventDef] = {}
        self.flows: dict[str, FlowDef] = {}
        self.objects: dict[str, ObjectSchema] = {}
        self.rules: dict[str, RuleDef] = {}
        self.actions: dict[str, ActionDef] = {}
        self.behaviors: dict[str, BehaviorDef] = {}
        self.instances: dict[str, list[dict]] = {}  # 对象实例

    # ── 加载 ──

    def load_from_yaml(self, path: str):
        """从 YAML 文件加载模型"""
        with open(path) as f:
            data = yaml.safe_load(f)
        for element_type, entries in data.items():
            if element_type == "events":
                for e in entries:
                    self.events[e["event_type"]] = EventDef(**e)
            elif element_type == "flows":
                for f_def in entries:
                    self.flows[f_def["flow_id"]] = FlowDef(**f_def)
            elif element_type == "objects":
                for o in entries:
                    self.objects[o["object_type"]] = ObjectSchema(**o)
            elif element_type == "rules":
                for r in entries:
                    self.rules[r["rule_id"]] = RuleDef(**r)
            elif element_type == "actions":
                for a in entries:
                    self.actions[a["action_id"]] = ActionDef(**a)
            elif element_type == "behaviors":
                for b in entries:
                    self.behaviors[b["behavior_id"]] = BehaviorDef(**b)
        return self

    # ── 查询接口 ──

    def get_event_def(self, event_type: str) -> EventDef | None:
        return self.events.get(event_type)

    def list_events(self, domain: str | None = None) -> list[EventDef]:
        if domain:
            return [e for e in self.events.values() if e.domain == domain]
        return list(self.events.values())

    def get_flow_def(self, flow_id: str) -> FlowDef | None:
        return self.flows.get(flow_id)

    def get_object_schema(self, object_type: str) -> ObjectSchema | None:
        return self.objects.get(object_type)

    def get_rule_def(self, rule_id: str) -> RuleDef | None:
        return self.rules.get(rule_id)

    def list_rules(self, domain: str | None = None) -> list[RuleDef]:
        if domain:
            return [r for r in self.rules.values() if r.domain == domain]
        return list(self.rules.values())

    def get_behavior_def(self, behavior_id: str) -> BehaviorDef | None:
        return self.behaviors.get(behavior_id)

    # ── 元信息 ──

    def metadata(self) -> dict:
        return {
            "name": "EAF Light WorldModel",
            "version": "0.1.0",
            "events": len(self.events),
            "flows": len(self.flows),
            "objects": len(self.objects),
            "rules": len(self.rules),
            "behaviors": len(self.behaviors),
        }


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str = "evt") -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
