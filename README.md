# Enterprise Agent Framework — 三层智能体架构

> **L0 决策智能体 · L1 运营智能体 · L2 个人助手**
> 从「人+系统」到「智能体网络」，AI 原生企业的组织架构框架

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-37%2F37-passing-green)]()
[![Status](https://img.shields.io/badge/Status-Alpha-yellow)]()

---

## 核心理念

```text
         L0: 决策智能体
         🧠 全量认知 · 战略编排 · 顶级LLM
                      │ 编排 / 调度
         L1: 运营智能体
         🏭 8大价值流 · 领域闭环 · 规则驱动
                      │ 遇「人节点」→ 调度分身
         L2: 个人助手
         👤 认知镜像 · 工具调用 · 风格模仿
```

| 层级 | 名称 | 认知范围 | 核心技术 |
|------|------|---------|---------|
| **L0** | 决策智能体 | 企业全量五要素模型 | 战略推理 + L1 编排 |
| **L1** | 运营智能体 | 领域级业务闭环 | 规则引擎 + 行为执行 |
| **L2** | 个人助手 | 个人工作知识 | 知识库 + 工具调用 |

---

## 轻量化版本 (`agent_light/`)

**零 Docker 依赖，单进程 All-in-One，专为开发/演示/单机部署设计。**

```text
agent_light/
├── main.py              ← FastAPI 入口 (端口 6010)
├── core.py              ← 五要素核心类型 + WorldModelProvider
├── agents.py            ← L0/L1/L2 三层智能体实现
├── rules.py             ← 数值规则 + LLM 语义规则引擎
├── knowledge.py         ← SQLite 持久化层
├── tools.py             ← 工具注册表 (通知/报告/知识/日程)
├── config.yaml          ← 应用配置
├── requirements.txt     ← 仅 6 个依赖
└── tests/
    └── test_e2e.py      ← 37 个端到端测试
```

### 快速启动

```bash
cd agent_light/
pip install -r requirements.txt
uvicorn agent_light.main:app --reload --port 6010
```

### API 一览

| 端点 | 作用 |
|------|------|
| `POST /api/v1/l0/plan` | L0 战略规划 (目标→任务拆解→L1 编排) |
| `POST /api/v1/l1/event` | L1 事件处理 (事件→规则判定→行为触发) |
| `POST /api/v1/l2/execute` | L2 任务执行 (任务→知识查询→工具调用) |
| `POST /api/v1/rules/evaluate` | 规则评估 (数值+语义双引擎) |
| `GET  /api/v1/agents/status` | 所有智能体状态 |

### 轻量化替换对照

| 生产概念 | 轻量实现 |
|---------|---------|
| 多进程 Agent 间 HTTP | 同进程直接方法调用 |
| 向量数据库 | SQLite + LLM 即时推理 |
| Temporal 工作流 | asyncio 状态机 |
| Redis 事件队列 | asyncio.Queue |
| 配置中心 (Consul) | config.yaml |

### 测试

```bash
cd agent_light/ && python3 -m pytest tests/ -v
# 37 passed ✅
```

---

## 三层智能体 × 五要素映射

| 五要素 | L0 决策智能体 | L1 运营智能体 | L2 个人助手 |
|--------|-------------|--------------|------------|
| 📡 **事件** | 全市场/全内部信号 | 流程触发信号 | 任务分配信号 |
| 🔀 **流程** | 企业级 SOP 编排 | 领域级业务闭环 | 个人级工作流 |
| 📦 **对象** | 企业全量实体视图 | 领域业务实体 | 个人工作对象 |
| 📐 **规则** | 战略/合规全局约束 | 业务流程规则 | 个人操作权限 |
| ⚡ **行为** | 调度/编排/决策 | 领域原子操作 | 个人工具操作 |

---

## L1 八大价值流

| 领域 | 职责 | 核心流程 |
|------|------|---------|
| 📈 商机捕获 | 市场信号、商机评分 | 线索→跟进→转化 |
| 📋 销售订单 | 订单全生命周期 | 报价→订单→交付 |
| 📄 合同审核 | 合同起草、审批 | 草拟→审核→签订→履约 |
| 🔬 研发交付 | 研发项目管理 | 需求→开发→测试→交付 |
| 📦 采购管理 | 供应商管理 | 寻源→招标→采购→验收 |
| 💰 财务结算 | 应收应付、对账 | 发票→付款→核销→对账 |
| 👥 人力资源 | 员工全生命周期 | 招聘→入职→考核→离职 |
| 🎧 客户服务 | 客服工单 | 投诉→分配→解决→回访 |
