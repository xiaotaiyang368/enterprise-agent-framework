"""
Enterprise Agent Framework — E5M Engine World Model Provider 实现参考

这是 WorldModelProvider 协议的一个实现，通过 HTTP 客户端连接到 E5M Engine 服务。
作为参考实现，展示了 Agent 框架如何与 E5M Engine 通信。
"""
import httpx
from specs.protocols.world_model_provider import (
    WorldModelProvider,
    EventDef, FlowDef, FlowStep, ObjectSchema, ObjectQuery,
    RuleDef, RuleOutput, RuleEvalResult,
    ActionDef, ActionHandler, ApprovalStep, ActionResult,
    EventIn, EventOut, ModelMetadata,
)


class E5MEngineProvider(WorldModelProvider):
    """
    通过 HTTP 连接到 E5M Engine 的世界模型实现。

    配置方式：
        provider = E5MEngineProvider(
            event_hub_url="http://localhost:8000",
            rule_engine_url="http://localhost:8001",
            action_bridge_url="http://localhost:8002",
        )
    """

    def __init__(
        self,
        event_hub_url: str = "http://localhost:8000",
        rule_engine_url: str = "http://localhost:8001",
        action_bridge_url: str = "http://localhost:8002",
    ):
        self.event_hub_url = event_hub_url.rstrip("/")
        self.rule_engine_url = rule_engine_url.rstrip("/")
        self.action_bridge_url = action_bridge_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30)

    # ── 规则判定 ──

    async def evaluate_rules(
        self, input_data: dict, rule_ids: list[str] | None = None
    ) -> RuleEvalResult:
        resp = await self._client.post(
            f"{self.rule_engine_url}/api/v1/rules/evaluate",
            json={"input_data": input_data, "rule_ids": rule_ids},
        )
        resp.raise_for_status()
        data = resp.json()
        return RuleEvalResult(**data)

    # ── 行为执行 ──

    async def execute_action(self, action_id: str, params: dict) -> ActionResult:
        resp = await self._client.post(
            f"{self.action_bridge_url}/api/v1/actions/execute",
            json={"action_id": action_id, "params": params},
        )
        resp.raise_for_status()
        data = resp.json()
        return ActionResult(**data)

    # ── 事件投递 ──

    async def ingest_event(self, event: EventIn) -> EventOut:
        resp = await self._client.post(
            f"{self.event_hub_url}/api/v1/events",
            json={
                "event_type": event.event_type,
                "source": event.source,
                "source_ref": event.source_ref,
                "payload": event.payload,
                "priority": event.priority,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return EventOut(**data)

    # ── 事件查询 ──

    async def get_event_definition(self, event_type: str) -> EventDef | None:
        resp = await self._client.get(
            f"{self.event_hub_url}/api/v1/events",
            params={"event_type": event_type, "page_size": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        item = items[0]
        return EventDef(
            event_type=item["event_type"],
            name=item.get("event_name", ""),
            priority=item.get("priority", "mid"),
        )

    async def list_events(self, domain: str | None = None) -> list[EventDef]:
        # E5M Engine 的事件定义存储在 MD 文件中，通过设计态接口查询
        # 简化实现：返回所有已注册的事件类型
        resp = await self._client.get(
            f"{self.event_hub_url}/api/v1/events",
            params={"page_size": 200},
        )
        resp.raise_for_status()
        data = resp.json()
        seen = set()
        results = []
        for item in data.get("items", []):
            et = item["event_type"]
            if et not in seen:
                seen.add(et)
                results.append(EventDef(
                    event_type=et,
                    name=item.get("event_name", ""),
                    priority=item.get("priority", "mid"),
                ))
        return results

    # ── 规则查询 ──

    async def get_rule_definitions(
        self, rule_ids: list[str] | None = None
    ) -> list[RuleDef]:
        if rule_ids:
            results = []
            for rid in rule_ids:
                try:
                    resp = await self._client.get(
                        f"{self.rule_engine_url}/api/v1/rules/{rid}",
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append(RuleDef(
                            rule_id=data["rule_id"],
                            name=data["name"],
                            type=data.get("type", "numeric"),
                        ))
                except Exception:
                    continue
            return results
        # 无过滤条件时从注册表获取所有规则
        # 简化：E5M Engine 当前没有批量规则查询端点
        return []

    # ── 行为查询 ──

    async def get_action_definition(self, action_id: str) -> ActionDef | None:
        try:
            resp = await self._client.get(
                f"{self.action_bridge_url}/api/v1/actions/{action_id}",
            )
            if resp.status_code == 200:
                data = resp.json()
                return ActionDef(
                    action_id=data["action_id"],
                    name=data.get("name", ""),
                    level=data.get("level", 1),
                )
        except Exception:
            pass
        return None

    # ── 对象查询（暂未实现） ──

    async def get_object_schema(self, object_type: str) -> ObjectSchema | None:
        # E5M Engine 当前未提供直接的对象 Schema HTTP 接口
        # 需要 E5M 后续版本实现
        return None

    async def query_objects(self, query: ObjectQuery) -> list[dict]:
        return []

    async def get_flow_definition(self, flow_id: str) -> FlowDef | None:
        return None

    async def get_flow_steps(self, flow_id: str) -> list[FlowStep]:
        return []

    # ── 图查询 ──

    async def graph_query(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        # 暂未实现，需要 E5M Engine 的图查询 API
        return []

    # ── 元信息 ──

    async def get_model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="E5M Engine",
            version="0.1.0",
            description="五要素企业业务模型运行时引擎",
        )

    async def close(self):
        await self._client.aclose()
