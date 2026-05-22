# World Model Provider 协议

> Enterprise Agent Framework 与 E5M Engine（或其他世界模型实现）之间的通信契约

## 设计原则

```
Enterprise Agent Framework        E5M Engine (或其他实现)
                                   
┌─────────────────┐    协议     ┌─────────────────┐
│  L0 决策智能体   │ ◄───────► │   E5M Engine     │
│  L1 运营智能体   │            │   (Event Hub)     │
│  L2 个人助手     │            │   (Rule Engine)   │
│                  │            │   (Action Bridge) │
│  依赖: 协议接口   │            │   (Flow Engine)   │
│  不依赖具体实现   │            │   (知识图谱)      │
└─────────────────┘            └─────────────────┘
```

**核心原则：**
1. **面向接口编程** — EAF 依赖抽象协议，不依赖 E5M Engine 的具体实现
2. **协议第一** — 协议定义在 EAF 项目中，任何实现（E5M / 其他）都必须遵循
3. **可替换性** — 世界模型可以替换为其他实现（如人工标注、第三方知识图谱、LLM 即时推理）
4. **运行时选择** — 通过配置指定使用哪个 World Model Provider，无需改代码

## 协议定义

### 1. 世界模型查询接口（World Model Query）

Agent 读取世界模型来理解业务上下文。

```python
class WorldModelProvider(ABC):
    """世界模型提供者 — 抽象接口"""

    # ── 事件相关 ──
    @abstractmethod
    async def get_event_definition(self, event_type: str) -> EventDef | None:
        """获取事件定义"""
        ...

    @abstractmethod
    async def list_events(self, domain: str | None = None) -> list[EventDef]:
        """获取某领域的所有事件定义"""
        ...

    # ── 流程相关 ──
    @abstractmethod
    async def get_flow_definition(self, flow_id: str) -> FlowDef | None:
        """获取流程定义"""
        ...

    @abstractmethod
    async def get_flow_steps(self, flow_id: str) -> list[FlowStep]:
        """获取流程的步骤列表"""
        ...

    # ── 对象相关 ──
    @abstractmethod
    async def get_object_schema(self, object_type: str) -> ObjectSchema | None:
        """获取对象模型定义（属性、状态机、关系）"""
        ...

    @abstractmethod
    async def query_objects(self, query: ObjectQuery) -> list[dict]:
        """查询业务对象实例"""
        ...

    # ── 规则相关 ──
    @abstractmethod
    async def get_rule_definitions(self, rule_ids: list[str] | None = None) -> list[RuleDef]:
        """获取规则定义"""
        ...

    @abstractmethod
    async def evaluate_rules(self, input_data: dict, rule_ids: list[str] | None = None) -> RuleEvalResult:
        """执行规则判定"""
        ...

    # ── 行为相关 ──
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
        """向世界模型投递事件（触发后续流程）"""
        ...

    # ── 图查询 ──
    @abstractmethod
    async def graph_query(self, query: str, params: dict | None = None) -> list[dict]:
        """查询知识图谱（关联方穿透、关系链分析）"""
        ...

    # ── 元信息 ──
    @abstractmethod
    async def get_model_metadata(self) -> ModelMetadata:
        """获取世界模型的版本信息"""
        ...
```

### 2. 事件对象定义

```python
@dataclass
class EventDef:
    """事件定义（对应 MD 中的事件模型）"""
    event_type: str
    name: str
    domain: str
    description: str
    trigger_condition: str          # 触发条件描述
    data_sources: list[str]         # 数据源
    related_rules: list[str]        # 关联规则
    priority: str                   # high / mid / low

@dataclass
class FlowDef:
    """流程定义（对应 MD 中的流程模型）"""
    flow_id: str
    name: str
    domain: str
    steps: list[FlowStep]
    triggers: list[str]             # 触发事件类型列表
    timeout: int | None             # 超时秒数

@dataclass
class ObjectSchema:
    """对象模型（对应 MD 中的对象模型）"""
    object_type: str
    attributes: list[AttributeDef]
    state_machine: dict             # 状态转换图
    relationships: list[RelationshipDef]
    related_events: list[str]

@dataclass
class RuleDef:
    """规则定义（对应 MD 中的规则模型）"""
    rule_id: str
    name: str
    type: str                       # numeric / semantic
    description: str
    policy_ref: str | None          # 政策出处
    condition: dict | None          # 数值型规则的判定条件
    prompt_template: str | None     # 语义型规则的 LLM Prompt
    output: RuleOutput

@dataclass
class ActionDef:
    """行为定义（对应 MD 中的行为模型）"""
    action_id: str
    name: str
    level: int                      # 1-4
    handlers: list[ActionHandler]
    approval_chain: list[ApprovalStep]
```

### 3. 运行时状态对象

```python
@dataclass
class EventIn:
    event_type: str
    source: str
    source_ref: str | None
    payload: dict
    priority: str = "mid"

@dataclass  
class EventOut:
    event_id: str
    event_type: str
    status: str

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
    status: str                     # started / completed / failed / awaiting_approval
    output: dict | None
```

## 实现示例

### E5M Engine 实现

```python
from enterprise_agent_framework.protocols import WorldModelProvider

class E5MEngineProvider(WorldModelProvider):
    """E5M Engine 的世界模型实现"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def evaluate_rules(self, input_data: dict, rule_ids=None) -> RuleEvalResult:
        resp = await self.client.post("/api/v1/rules/evaluate", json={
            "input_data": input_data,
            "rule_ids": rule_ids,
        })
        data = resp.json()
        return RuleEvalResult(**data)

    async def execute_action(self, action_id: str, params: dict) -> ActionResult:
        resp = await self.client.post("/api/v1/actions/execute", json={
            "action_id": action_id,
            "params": params,
        })
        data = resp.json()
        return ActionResult(**data)

    # ... 其他方法类似
```

### LLM-Only 实现（备选）

```python
class LLMWorldModelProvider(WorldModelProvider):
    """不依赖 E5M Engine，完全由 LLM 即时推理的世界模型"""

    def __init__(self, llm_client, model_defs: dict):
        self.llm = llm_client
        self.model_defs = model_defs  # MD 模型文件内容

    async def evaluate_rules(self, input_data: dict, rule_ids=None) -> RuleEvalResult:
        # 将 MD 中的规则定义作为 LLM 上下文，让 LLM 做规则判定
        prompt = f"""
        作为虚假贸易审查专家，请根据以下规则判定输入数据：
        
        规则定义：
        {self.model_defs['rules']}
        
        输入数据：
        {json.dumps(input_data, ensure_ascii=False)}
        
        请逐条判断是否命中规则，输出格式：...
        """
        response = await self.llm.chat(prompt)
        return self._parse_llm_result(response)

    async def execute_action(self, action_id: str, params: dict) -> ActionResult:
        # LLM 模拟执行行为（记录到审计日志）
        ...
```

## 两种模式的对比

| 维度 | E5M Engine 模式 | LLM-Only 模式 |
|------|----------------|---------------|
| **规则判定** | 数值规则 5ms + 语义规则 ~3s | 全部 LLM ~5-10s |
| **可靠性** | 数值规则确定性强 | 取决于 LLM 输出稳定性 |
| **可审计性** | 数值规则有确定性的执行路径 | 需要 LLM 调用日志 |
| **部署复杂度** | 需要 PG/Redis/Kafka/Temporal | 只需要 LLM API |
| **适用场景** | 生产级监管场景 | 原型验证/非关键路径 |
| **成本** | 低（数值规则免费） | 高（每次判定调 LLM） |

## 协议文件的组织

```
enterprise-agent-framework/
└── specs/protocols/
    ├── world-model-provider.md     ← 本文件（协议定义）
    ├── world-model-provider.py     ← Python 抽象基类
    └── e5m-engine-implementation.py ← E5M Engine 实现参考

e5m-engine/
└── README.md                        ← 说明自己是 World Model Provider 的实现
```
