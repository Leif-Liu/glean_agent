# Glean Agent 优化指南

## 📊 架构对比

### 原始架构（外部 LLM）

```
用户问题
    ↓
┌─────────────────────────────────────────────────┐
│  问题分析 (本地规则)                     │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  问题分解 (本地规则)                     │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  Glean Search API                         │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  文档检索 (HTTP/Retriever)              │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  外部 LLM 分析 (vLLM/OpenAI API)        │
│  - 一致性分析                              │
│  - 矛盾识别                                │
│  - 信息综合                                  │
└─────────────────────────────────────────────────┘
    ↓
答案 + 置信度
```

### 优化架构（Glean Chat API）

```
用户问题
    ↓
┌─────────────────────────────────────────────────┐
│  Glean Chat API (一站式服务)              │
│  - 自动搜索                                 │
│  - 内置 LLM                                 │
│  - 权限管理                                 │
│  - 来源引用                                 │
└─────────────────────────────────────────────────┘
    ↓
答案 + 来源
```

---

## ✅ 优化优势

| 方面 | 原始方案 | 优化方案 | 改进 |
|------|---------|---------|------|
| **基础设施** | 需要自建 vLLM 服务 | ✅ Glean 内置 | 减少运维 |
| **代码复杂度** | 高（HTTP 请求/JSON 解析） | ✅ 低（SDK 调用） | 更易维护 |
| **权限管理** | 需要自己实现 | ✅ 自动继承 Glean 权限 | 更安全 |
| **搜索集成** | 手动调用 Search API | ✅ 自动搜索 | 更简洁 |
| **响应速度** | 多次 API 调用 | ✅ 单次 API 调用 | 更快 |
| **配置要求** | 需要 LLM_BASE_URL、API Key | ✅ 仅需 Glean 凭证 | 更简单 |
| **维护成本** | 高（两个服务） | ✅ 低（单一服务） | 更经济 |

---

## 🔄 迁移指南

### 场景 1：简单问答

**原始代码：**
```python
from core.agent import GleanAI

agent = GleanAI()
response = agent.query("公司远程工作政策是什么？")
```

**优化代码：**
```python
from core.glean_chat_agent import create_context_agent

agent = create_context_agent()
response = agent.query("公司远程工作政策是什么？")
```

**优势：**
- 无需配置外部 LLM
- 代码更简洁
- 自动搜索和回答

---

### 场景 2：使用自定义 Agent

**步骤 1：在 Glean Agent Builder 中创建 Agent**
1. 访问 `https://your-instance.glean.com/admin/agents`
2. 创建新的 Agent，配置其技能和知识库
3. 从 URL 中获取 Agent ID

**步骤 2：在代码中使用**
```python
from core.glean_chat_agent import create_agent_with_id

agent = create_agent_with_id(agent_id="your-agent-123")
response = agent.query("你的问题", with_context=False)
```

**优势：**
- 在 Glean 界面中可视化配置 Agent
- 复用企业级的 Agent 能力
- 无需维护自定义 LLM 提示词

---

## 📁 新增文件

| 文件 | 说明 |
|------|------|
| `modules/glean_chat_wrapper.py` | Glean Chat 和 Agents API 封装 |
| `core/glean_chat_agent.py` | 优化的智能体实现 |
| `docs/OPTIMIZATION_GUIDE.md` | 本优化指南 |

---

## 🚀 运行新模式

### 优化演示
```bash
python main.py glean-chat-demo
```

### 优化交互模式
```bash
python main.py glean-chat-interactive
```

### 列出可用 Agents
```bash
python main.py agents
```

### 使用特定 Agent
```bash
python main.py agent <agent_id> "你的问题"
```

---

## 📝 配置变更

### 环境变量

**优化模式下，以下变量不再需要：**
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_API_KEY`
- `LLM_TEMPERATURE`
- `LLM_TOP_P`
- `LLM_TOP_K`
- `LLM_MAX_TOKENS`
- `LLM_TIMEOUT`

**仅需保留：**
- `GLEAN_INSTANCE`
- `GLEAN_CLIENT_API_TOKEN`
- `GLEAN_INDEXING_TOKEN`

### config/config.py

`LLMConfig` 仍然存在，但在优化模式下不会被使用。

---

## ⚠️ 注意事项

1. **功能差异**
   - 原始模式支持更细粒度的分析步骤控制
   - 优化模式依赖 Glean 的内置能力

2. **定制化**
   - 如果需要完全控制 LLM 提示词，仍可使用原始模式
   - Glean Agent Builder 支持一定程度的自定义

3. **性能**
   - 优化模式通常更快（减少 API 调用次数）
   - 适合大多数企业问答场景

---

## 📚 相关文档

- [Glean Chat API](https://developers.glean.com/api/client-api/chat/chat)
- [Glean Agents API](https://developers.glean.com/api/client-api/agents/overview)
- [Agent Builder](https://your-instance.glean.com/admin/agents)
