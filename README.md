# Enterprise Agent Framework — 三层智能体架构

> **L0 决策智能体 · L1 运营智能体 · L2 个人助手**  
> 从「人+系统」到「智能体网络」，AI 原生企业的组织架构框架

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-yellow)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)

---

## 核心理念

传统企业是一个「人+系统」的集合体。信息沿科层逐级上报，层层衰减；部门间数据割裂，全局认知缺失；员工主动找事，系统是被动工具。

在 AI 原生时代，企业不再是一个科层制的机械组织，而是一个**多层级协同的智能体网络**。

```
         ┌─────────────────────────────────┐
         │  L0: 决策智能体                   │
         │  🧠 全量认知 · 战略编排 · 顶级LLM  │
         └────────────┬────────────────────┘
                      │ 编排 / 调度
         ┌────────────▼────────────────────┐
         │  L1: 运营智能体                   │
         │  🏭 8大价值流 · 领域闭环 · 自主执行 │
         └────────────┬────────────────────┘
                      │ 遇「人节点」→ 调度分身
         ┌────────────▼────────────────────┐
         │  L2: 个人助手                     │
         │  👤 认知镜像 · 行动镜像 · 风格镜像  │
         └─────────────────────────────────┘
```

### 三层智能体

| 层级 | 名称 | 职责 | 认知范围 | 核心技术 |
|------|------|------|---------|---------|
| **L0** | 决策智能体 | 企业战略认知、编排 L1、资源调度 | 全量五要素模型 | 顶级 LLM 推理/规划 |
| **L1** | 运营智能体 | 按价值流拆分的专业流程执行 | 领域级业务闭环 | 规则引擎 + 流程引擎 |
| **L2** | 个人助手 | 数字分身、任务级执行 | 个人工作知识 | 知识习得 + 工具调用 |

---

## 五要素 × 三层映射

每个智能体层对五要素（事件·流程·对象·规则·行为）有不同的粒度和视角：

| 五要素 | L0 决策智能体 | L1 运营智能体 | L2 个人助手 |
|--------|-------------|--------------|------------|
| 📡 **事件** | 全市场/全内部信号 | 流程触发信号 | 任务分配信号 |
| 🔀 **流程** | 企业级 SOP 编排 | 领域级业务闭环 | 个人级工作流 |
| 📦 **对象** | 企业全量实体视图 | 领域业务实体 | 个人工作对象 |
| 📐 **规则** | 战略/合规全局约束 | 业务流程规则 | 个人操作权限 |
| ⚡ **行为** | 调度/编排/决策 | 领域原子操作 | 个人工具操作 |

---

## 智能体能力模型

### L0 决策智能体

```
🧠 认知: 全量企业业务模型视图 — 五要素全景
👁️ 感知: 内外部事件/请求全触达 — 市场信号 + 内部事件流
🚀 行动: 编排 L1 运营智能体 + 个人助手调度
⚡ 引擎: 顶级大模型 — 推理 · 规划 · 决策 · 工具调用
```

**典型能力：**
- 企业级战略目标分解与任务下发
- L1 运营智能体编排与弹性调度
- 跨域资源动态分配与冲突仲裁
- 执行反馈闭环与策略优化

### L1 运营智能体

L1 按企业价值流拆分为 8 个独立智能体：

| 领域 | 职责 | 核心流程 |
|------|------|---------|
| 📈 商机捕获 | 市场信号采集、商机评分 | 线索 → 跟进 → 转化 |
| 📋 销售订单 | 订单全生命周期管理 | 报价 → 订单 → 交付 |
| 📄 合同审核 | 合同起草、审批、履约 | 草拟 → 审核 → 签订 → 履约 |
| 🔬 研发交付 | 研发项目管理 | 需求 → 开发 → 测试 → 交付 |
| 📦 采购管理 | 供应商管理、采购执行 | 寻源 → 招标 → 采购 → 验收 |
| 💰 财务结算 | 应收应付、对账核销 | 发票 → 付款 → 核销 → 对账 |
| 👥 人力资源 | 员工全生命周期 | 招聘 → 入职 → 考核 → 离职 |
| 🎧 客户服务 | 客服工单、满意度 | 投诉 → 分配 → 解决 → 回访 |

**每个 L1 智能体都拥有：**
- 独立的领域知识库和业务规则
- 流程编排引擎（Temporal / Camunda）
- 事件感知 + 规则判定 + 行为执行闭环

### L2 个人助手

每个人类员工都有一个数字分身——个人助手。它习得主人的知识、经验、权限和操作能力。

```
🧬 认知镜像: 习得主人的知识体系与经验判断
🛠️ 行动镜像: 习得主人的操作习惯与工具使用
🎭 风格镜像: 习得主人的沟通风格与表达方式
🔐 权限映射: 继承主人的系统权限与操作边界
```

**典型角色：**
- **财务行政助手** — 报销审核、发票核验、预算跟踪
- **产品研发助手** — 技术文档编写、代码 Review、需求分析
- **售前方案助手** — 方案编写、竞品分析、客户沟通
- **秘书** — 日程管理、会议安排、任务委派

---

## 与五要素运行时引擎的关系

```
Enterprise Agent Framework           E5M Engine (或其他实现)
「谁来做」                              「做什么」
                                       
┌─────────────────┐    协议接口     ┌─────────────────┐
│  L0 决策智能体   │ ◄────────────► │   E5M Engine     │
│  L1 运营智能体   │  World Model   │   (Event Hub)     │
│  L2 个人助手     │  Provider      │   (Rule Engine)   │
│                  │  Protocol      │   (Action Bridge) │
│  依赖: 协议接口   │                │   (Flow Engine)   │
│  不依赖具体实现   │                │   (知识图谱)      │
└─────────────────┘                └─────────────────┘
```

**设计要点：**

1. **EAF 面向接口编程** — 通过 `WorldModelProvider` 抽象协议获取世界模型，不直接依赖 E5M Engine
2. **可替换性** — 世界模型可替换为 LLM-Only 实现、第三方知识图谱或其他系统
3. **E5M Engine 是参考实现** — 位于 [specs/protocols/](specs/protocols/) 中的协议定义和实现参考
4. **运行时选择** — 通过配置指定 Provider 类型，无需改代码

### 协议接口

World Model Provider 协议定义在 `specs/protocols/world_model_provider.py`，包含：

| 能力 | 说明 |
|------|------|
| 事件查询/投递 | 读取事件定义、投递新事件 |
| 流程查询 | 读取流程定义和步骤 |
| 对象查询 | 读取对象 Schema 和实例 |
| 规则判定 | 执行规则并获取结果 |
| 行为执行 | 执行预定义的行为 |
| 图查询 | 关联方穿透和关系分析 |

切换 Provider 示例：

```python
# 使用 E5M Engine
from specs.protocols.e5m_engine_implementation import E5MEngineProvider
provider = E5MEngineProvider(
    event_hub_url="http://localhost:8000",
    rule_engine_url="http://localhost:8001",
)

# 使用 LLM-Only（不依赖 E5M Engine）
from my_impl.llm_provider import LLMWorldModelProvider
provider = LLMWorldModelProvider(llm_client, model_defs=...)

# Agent 使用 provider
result = await provider.evaluate_rules(input_data={...})
```

---

## 快速开始

```bash
# 克隆项目
git clone https://github.com/xiaotaiyang368/enterprise-agent-framework.git
cd enterprise-agent-framework

# 安装
pip install -r requirements.txt

# 查看各层规范
cat specs/l0-decision-agent.md
cat specs/l1-operation-agent.md
cat specs/l2-personal-assistant.md

# 运行示例
python examples/l0-decision-agent/strategic_planning.py
```

---

## 开发路线图

```
Phase 1 (2周) ── L2 个人助手 MVP
  → 个人知识习得管线
  → 工具调用框架（API + Browser Use）
  → 角色配置模板

Phase 2 (3周) ── L1 运营智能体
  → 领域智能体 SDK
  → 流程编排集成（对接 E5M Engine）
  → 8 个领域智能体模板

Phase 3 (2周) ── L0 决策智能体
  → 战略认知引擎
  → L1 编排调度器
  → 跨域协作仲裁

Phase 4 (2周) ── 三层协同
  → 全链路测试
  → 性能优化
  → 文档与示例
```

## 许可证

[Apache License 2.0](LICENSE)

## 相关项目

- [e5m-engine](https://github.com/xiaotaiyang368/e5m-engine) — 五要素企业业务模型运行时引擎
