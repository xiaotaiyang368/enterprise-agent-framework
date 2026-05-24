"""
EAF Light — 知识存储 (SQLite)
三层共享的知识持久化层
"""
from __future__ import annotations
import sqlite3, json, os
from datetime import datetime, timezone
from typing import Any


DB_PATH = os.environ.get("EAF_DB_PATH", "data/eaf_knowledge.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    with _conn() as conn:
        conn.executescript("""
        -- L0: 战略与规划
        CREATE TABLE IF NOT EXISTS strategic_plans (
            plan_id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            domain TEXT,
            tasks TEXT NOT NULL DEFAULT '[]',
            status TEXT DEFAULT 'active',
            result TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- L1: 事件与执行记录
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            domain TEXT NOT NULL,
            source TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            status TEXT DEFAULT 'received',
            risk_level TEXT,
            risk_score REAL,
            actions TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- L2: 任务与知识
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            goal TEXT NOT NULL,
            context TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            output TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- 知识条目
        CREATE TABLE IF NOT EXISTS knowledge_items (
            item_id TEXT PRIMARY KEY,
            agent_type TEXT NOT NULL,
            domain TEXT,
            category TEXT,  -- fact / rule / experience / skill
            content TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- 审计日志
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            component TEXT NOT NULL,
            operation TEXT NOT NULL,
            actor TEXT,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- 图谱边（关系追踪）
        CREATE TABLE IF NOT EXISTS graph_edges (
            edge_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_type TEXT,
            target_id TEXT NOT NULL,
            target_type TEXT,
            relation TEXT NOT NULL,
            properties TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)


# ── L0 战略 ──

def save_plan(plan_id: str, goal: str, tasks: list[dict], domain: str = ""):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO strategic_plans (plan_id, goal, domain, tasks, status) VALUES (?,?,?,?,?)",
            (plan_id, goal, domain, json.dumps(tasks, ensure_ascii=False), "active"),
        )

def update_plan_status(plan_id: str, status: str, result: dict = None):
    with _conn() as conn:
        conn.execute(
            "UPDATE strategic_plans SET status=?, result=? WHERE plan_id=?",
            (status, json.dumps(result, ensure_ascii=False) if result else None, plan_id),
        )

def list_plans(limit: int = 20) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM strategic_plans ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── L1 事件 ──

def save_event(event_id: str, event_type: str, domain: str, source: str,
               payload: dict, status: str = "received"):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO events (event_id, event_type, domain, source, payload, status) VALUES (?,?,?,?,?,?)",
            (event_id, event_type, domain, source, json.dumps(payload, ensure_ascii=False), status),
        )

def update_event_result(event_id: str, risk_level: str, risk_score: float, actions: list[str]):
    with _conn() as conn:
        conn.execute(
            "UPDATE events SET risk_level=?, risk_score=?, actions=?, status='processed' WHERE event_id=?",
            (risk_level, risk_score, json.dumps(actions), event_id),
        )

def list_events(domain: str | None = None, limit: int = 50) -> list[dict]:
    with _conn() as conn:
        if domain:
            rows = conn.execute(
                "SELECT * FROM events WHERE domain=? ORDER BY created_at DESC LIMIT ?",
                (domain, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── L2 任务与知识 ──

def save_task(task_id: str, agent_id: str, goal: str, context: dict | None = None):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tasks (task_id, agent_id, goal, context, status) VALUES (?,?,?,?,?)",
            (task_id, agent_id, goal, json.dumps(context or {}, ensure_ascii=False), "pending"),
        )

def update_task_result(task_id: str, status: str, output: dict | None = None):
    with _conn() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, output=? WHERE task_id=?",
            (status, json.dumps(output, ensure_ascii=False) if output else None, task_id),
        )

def add_knowledge(agent_type: str, category: str, content: str,
                  domain: str = "", tags: list[str] | None = None,
                  confidence: float = 1.0):
    import uuid
    item_id = f"know-{uuid.uuid4().hex[:12]}"
    with _conn() as conn:
        conn.execute(
            "INSERT INTO knowledge_items (item_id, agent_type, domain, category, content, tags, confidence) VALUES (?,?,?,?,?,?,?)",
            (item_id, agent_type, domain, category, content,
             json.dumps(tags or []), confidence),
        )
    return item_id

def query_knowledge(agent_type: str | None = None, domain: str | None = None,
                    category: str | None = None, limit: int = 20) -> list[dict]:
    with _conn() as conn:
        parts = ["SELECT * FROM knowledge_items WHERE 1=1"]
        params = []
        if agent_type:
            parts.append("AND agent_type=?")
            params.append(agent_type)
        if domain:
            parts.append("AND domain=?")
            params.append(domain)
        if category:
            parts.append("AND category=?")
            params.append(category)
        parts.append("ORDER BY confidence DESC, created_at DESC LIMIT ?")
        params.append(limit)
        rows = conn.execute(" ".join(parts), params).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── 图谱 ──

def add_edge(source_id: str, target_id: str, relation: str,
             source_type: str = "", target_type: str = "",
             properties: dict | None = None):
    import uuid
    edge_id = f"edge-{uuid.uuid4().hex[:12]}"
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO graph_edges (edge_id, source_id, source_type, target_id, target_type, relation, properties) VALUES (?,?,?,?,?,?,?)",
            (edge_id, source_id, source_type, target_id, target_type, relation,
             json.dumps(properties or {})),
        )
    return edge_id

def query_graph(source_id: str | None = None, relation: str | None = None) -> list[dict]:
    with _conn() as conn:
        parts = ["SELECT * FROM graph_edges WHERE 1=1"]
        params = []
        if source_id:
            parts.append("AND (source_id=? OR target_id=?)")
            params.extend([source_id, source_id])
        if relation:
            parts.append("AND relation=?")
            params.append(relation)
        rows = conn.execute(" ".join(parts), params).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── 审计 ──

def audit(trace_id: str, component: str, operation: str,
          actor: str = "system", detail: dict | None = None):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (trace_id, component, operation, actor, detail) VALUES (?,?,?,?,?)",
            (trace_id, component, operation, actor,
             json.dumps(detail, ensure_ascii=False) if detail else None),
        )

def list_audit(limit: int = 50) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── 辅助 ──

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # 解析 JSON 字段
    for key in ("payload", "tasks", "actions", "context", "output",
                "detail", "properties", "tags", "content"):
        if key in d and isinstance(d[key], str) and d[key]:
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                pass
    return d
