"""
EAF Light — 工具注册表
L2 个人助手可调用的技能
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("eaf.tools")


class Tool:
    """一个可调用的工具/技能"""
    def __init__(self, tool_id: str, name: str, description: str,
                 handler: Callable, params_schema: dict | None = None):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.handler = handler
        self.params_schema = params_schema or {}

    async def execute(self, params: dict) -> dict:
        try:
            result = self.handler(params)
            if isinstance(result, Coroutine):
                result = await result
            return {"success": True, "output": result}
        except Exception as e:
            logger.error(f"工具 [{self.tool_id}] 执行失败: {e}")
            return {"success": False, "error": str(e)}


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> Tool | None:
        return self._tools.get(tool_id)

    def list(self) -> list[dict]:
        return [
            {"tool_id": t.tool_id, "name": t.name,
             "description": t.description, "params_schema": t.params_schema}
            for t in self._tools.values()
        ]

    def unregister(self, tool_id: str):
        self._tools.pop(tool_id, None)


# ── 内置工具定义 ──

def _send_notification(params: dict) -> dict:
    """发送通知（模拟）"""
    channel = params.get("channel", "飞书")
    recipients = params.get("recipients", [])
    message = params.get("message", "")
    logger.info(f"[通知] 通过 {channel} 发送给 {recipients}: {message}")
    return {
        "status": "sent",
        "channel": channel,
        "recipients": recipients,
        "message_length": len(message),
    }

def _generate_report(params: dict) -> dict:
    """生成审批报告（模拟）"""
    title = params.get("title", "审批报告")
    content = params.get("content", "")
    report_type = params.get("type", "approval")
    logger.info(f"[报告] 生成 {report_type} 报告: {title}")
    return {
        "status": "generated",
        "title": title,
        "type": report_type,
        "report_id": f"rpt-{hash(content) % 100000:06d}",
        "page_count": max(1, len(content) // 500 + 1),
    }

def _query_knowledge(params: dict) -> dict:
    """查询知识库（模拟）"""
    topic = params.get("topic", "")
    logger.info(f"[知识] 查询: {topic}")
    return {
        "status": "found",
        "topic": topic,
        "results": [
            {"title": f"{topic}相关政策", "summary": f"关于{topic}的企业规定..."},
            {"title": f"{topic}历史案例", "summary": f"过往{topic}处理记录..."},
        ],
    }

def _schedule_meeting(params: dict) -> dict:
    """安排会议（模拟）"""
    title = params.get("title", "会议")
    participants = params.get("participants", [])
    duration = params.get("duration_minutes", 30)
    logger.info(f"[日程] 安排会议: {title}, 参与人: {participants}")
    return {
        "status": "scheduled",
        "meeting_id": f"mtg-{hash(str(params)) % 100000:06d}",
        "title": title,
        "duration_minutes": duration,
    }

def register_default_tools(registry: ToolRegistry):
    """注册内置工具"""
    registry.register(Tool(
        "tool-notify", "发送通知", "通过飞书/邮件等渠道发送通知",
        _send_notification,
        {"channel": {"type": "string", "description": "通知渠道"},
         "recipients": {"type": "list", "description": "接收人"},
         "message": {"type": "string", "description": "通知内容"}},
    ))
    registry.register(Tool(
        "tool-report", "生成报告", "生成审批报告或分析报告",
        _generate_report,
        {"title": {"type": "string"}, "content": {"type": "string"},
         "type": {"type": "string", "description": "报告类型"}},
    ))
    registry.register(Tool(
        "tool-knowledge", "查询知识库", "查询企业内部知识库",
        _query_knowledge,
        {"topic": {"type": "string", "description": "查询主题"}},
    ))
    registry.register(Tool(
        "tool-schedule", "安排会议", "安排会议并发送邀请",
        _schedule_meeting,
        {"title": {"type": "string"}, "participants": {"type": "list"},
         "duration_minutes": {"type": "number"}},
    ))
    logger.info(f"已注册 {len(registry._tools)} 个内置工具")


# 全局工具注册表
tool_registry = ToolRegistry()
