# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Glean AI Agent is an intelligent enterprise knowledge assistant built on the Glean API. It performs question decomposition, deep analysis, intelligent search, and comprehensive summarization. The codebase is in Python (~6,000 lines) and follows a pipeline architecture with distinct phases for analysis, planning, execution, and synthesis.

The project also includes a **JQL Action Server** - a Glean Action that converts natural language queries into valid Jira JQL (Jira Query Language) with runtime validation.

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with Glean credentials (GLEAN_INSTANCE, GLEAN_CLIENT_API_TOKEN, GLEAN_INDEXING_TOKEN)
```

### Running
```bash
# Demo mode with 5 sample queries
python main.py demo

# Interactive mode for ad-hoc questions
python main.py interactive

# Single query
python main.py "your question here"

# Action Server (JQL Conversion)
python main.py action-server
```

### Development
```bash
# Run tests (requires valid Glean config)
python -m pytest tests/

# Code formatting
black .
isort .

# Type checking
mypy .

# View logs
tail -f logs/agent.log
```

## High-Level Architecture

### Pipeline Flow
```
User Query
  ↓
[Analysis] QuestionAnalyzer → Intent, Complexity, Entities
  ↓
[Planning] QuestionPlanner → Task decomposition, Dependencies
  ↓
[Execution] TaskOrchestrator → Parallel task execution
  ├─ GleanSearcher (4 search modes)
  ├─ DocumentRetriever (fetch full content)
  └─ ContentSummarizer (generate answers)
  ↓
[Synthesis] ResponseBuilder → Format and return
```

### Core Components

**core/agent.py** (`GleanAI` class) - Main orchestrator that coordinates the 4-phase pipeline. Initializes all components and manages LLM integration via OpenAI-compatible API (vLLM).

**core/analyzer.py** (`QuestionAnalyzer`) - Analyzes question intent, complexity (4 levels), and extracts entities with scoring.

**core/planner.py** (`QuestionPlanner`) - Decomposes questions into steps based on complexity. Simple = direct search, VeryComplex = multi-stage exploration with entity/broad/historical searches.

**core/orchestrator.py** (`TaskOrchestrator`) - DAG-based task scheduler with topological sort, parallel execution with semaphore control, circular dependency detection.

**modules/searcher.py** (`GleanSearcher`) - 4 search modes: Basic (keyword), Semantic (query expansion), Hybrid (parallel both + rerank), Deep (3-round iteration).

**modules/retriever.py** (`DocumentRetriever`) - Batch document fetching via HTTP/Glean API, HTML cleaning, deduplication.

**modules/summarizer.py** (`ContentSummarizer`) - Answer generation with 4 answer types: policy, procedure, comparison, general. Includes confidence scoring.

### Action Server Components

**actions/server.py** (`FastAPI`) - Web server for JQL conversion with endpoints: `/convert_to_jql`, `/health`, `/config`.

**actions/jql_converter.py** (`JQLConverter`) - Converts natural language to JQL using Glean Chat API with few-shot learning.

**actions/jql_validator.py** (`JQLValidator`) - Validates JQL against Jira REST API with OAuth 2.0 authentication.

**prompts/jql_conversion.py** - JQL conversion prompt templates with syntax examples and error handling.

### Key Patterns

1. **Strategy Pattern**: Multiple search modes (Basic, Semantic, Hybrid, Deep)
2. **Dependency Injection**: Components injected into TaskOrchestrator for flexibility
3. **Retry Pattern**: Exponential backoff via `utils/retry.py`
4. **Caching**: In-memory cache with TTL for search results

## Configuration

All configuration is managed via `config/config.py` using Pydantic models:

- `GleanConfig` - Glean API settings (instance, tokens)
- `AgentConfig` - Agent behavior (search mode, timeouts, cache)
- `LLMConfig` - LLM connection (OpenAI-compatible API like vLLM)
- `JiraConfig` - Jira OAuth configuration (domain, client ID/secret, cloud ID)
- `ActionServerConfig` - Action Server settings (host, port, logging)

Environment variables in `.env` override defaults. The LLM is optional - the agent falls back gracefully if not configured.

### Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GLEAN_INSTANCE` | required | Company Glean instance name |
| `GLEAN_CLIENT_API_TOKEN` | required | Client API token for search/chat |
| `GLEAN_INDEXING_TOKEN` | required | Indexing API token |
| `DEFAULT_SEARCH_MODE` | `hybrid` | Search strategy: basic/semantic/hybrid/deep |
| `ENABLE_DEEP_SEARCH` | `true` | Enable multi-round deep search |
| `MAX_SEARCH_RESULTS` | 10 | Results per search |
| `LLM_BASE_URL` | `http://localhost:8000/v1` | OpenAI-compatible LLM endpoint |
| `LLM_MODEL_NAME` | `Qwen/Qwen2.5-7B-Instruct` | Model to use |

## Search Modes & Complexity

| Complexity | Search Rounds | Example |
|------------|---------------|---------|
| Simple | 1 | "What is our WFH policy?" |
| Moderate | 2-3 | "How do I apply for leave?" |
| Complex | 3-5 | "Compare Drive vs SharePoint" |
| Very Complex | 5-7 | Multi-stage analysis queries |

## API Integration

The agent integrates with multiple Glean API endpoints:
- **Client API**: `/search`, `/chat`, `/autocomplete`
- **Indexing API**: `/adddatasource`, `/indexdocument`, `/getdocumentcount`
- **Agents API**: `/agents/runs`
- **Activity API**: `/activity`

Base URLs are constructed dynamically: `https://{instance}-be.glean.com/rest/api/v1`

## Testing

Tests require valid Glean credentials. Use `pytest` with `pytest-asyncio` for async tests. Test files should be placed in `tests/` directory.

## JQL Action Server

### Overview

The JQL Action Server is a Glean Action that converts natural language queries into valid Jira JQL (Jira Query Language) and validates them against Jira's REST API. This allows users to describe their Jira query needs in plain language and get executable JQL.

### Architecture

```
User Natural Language Query
  ↓
[Conversion] JQLConverter (Glean Chat API) → JQL Statement
  ↓
[Validation] JQLValidator (Jira REST API) → Syntax Check
  ↓
[Response] Return validated JQL to Glean Assistant
```

### Components

| File | Description |
|------|-------------|
| `actions/server.py` | FastAPI web server with endpoints |
| `actions/jql_converter.py` | NL → JQL conversion using Glean Chat API |
| `actions/jql_validator.py` | JQL validation via Jira REST API |
| `actions/openapi_spec.yaml` | OpenAPI spec for Glean Admin UI |
| `prompts/jql_conversion.py` | JQL conversion prompt templates |

### API Endpoints

- `POST /convert_to_jql` - Convert natural language to JQL
  - Request: `{"query": "Find all high priority bugs", "validate": true}`
  - Response: `{"success": true, "jql": "priority = \"Highest\" AND issuetype = \"Bug\"", "validated": true}`

- `GET /health` - Health check endpoint

- `GET /config` - OAuth configuration info for Glean Admin UI

### Configuration

Add to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ATLASSIAN_DOMAIN` | required | Your Jira domain (e.g., `your-company`) |
| `JIRA_CLIENT_ID` | required | OAuth Client ID from Atlassian console |
| `JIRA_CLIENT_SECRET` | required | OAuth Client Secret from Atlassian console |
| `JIRA_CLOUD_ID` | required | Jira Cloud ID for API calls |
| `ACTION_SERVER_HOST` | `0.0.0.0` | Server listen address |
| `ACTION_SERVER_PORT` | `8000` | Server listen port |

### Glean Integration

When configuring the Action in Glean Admin UI, use these OAuth settings:

- **Client URL**: `https://auth.atlassian.com/authorize?audience={ATLASSIAN_DOMAIN}.atlassian.net&prompt=consent`
- **Authorization URL**: `https://auth.atlassian.com/oauth/token`
- **Scopes**: `read:jira-work`, `read:jira-user`, `offline_access`

**Important**: The Client URL and Authorization URL are Atlassian's fixed endpoints and do NOT contain your Action Server's URL.

### OAuth Configuration Process

The OAuth 2.0 flow involves three different URL categories:

| URL Type | Belongs to | Contains Action Server URL | Purpose |
|-----------|---------------|---------------------------|---------|
| **Client URL** (Authorization URL) | Atlassian | ❌ No | User login/authorization page |
| **Authorization URL** (Token URL) | Atlassian | ❌ No | Exchange authorization code for access token |
| **Callback URL** (Redirect URL) | Your Action Server | ✅ Yes | Where Atlassian redirects after authorization |

#### Three-Step Configuration Process

**Step 1: Configure OAuth App in Atlassian Developer Console** (Do this first)

1. Go to https://developer.atlassian.com/console
2. Create a new OAuth 2.0 app:
   - App Name: `Glean JQL Action`
   - Callback URLs: `https://your-server.com/auth/callback` (YOUR server address)
   - Scopes: `read:jira-work`, `read:jira-user`
3. Save and note down:
   - Client ID
   - Client Secret

**Step 2: Configure Action in Glean Admin UI**

1. Go to Glean Admin > Tools > Actions
2. Create new Action:
   - Action Type: `Execution`
   - Action Endpoint: `https://your-server.com/convert_to_jql` (YOUR server address)
   - OpenAPI Spec: Upload `actions/openapi_spec.yaml`
   - OAuth Configuration (fixed Atlassian URLs):
     - Client URL: `https://auth.atlassian.com/authorize?audience={ATLASSIAN_DOMAIN}.atlassian.net&prompt=consent`
     - Authorization URL: `https://auth.atlassian.com/oauth/token`
     - Scopes: `read:jira-work`, `read:jira-user`, `offline_access`

**Step 3: Update `.env` with Credentials**

```bash
ATLASSIAN_DOMAIN=your-company
JIRA_CLIENT_ID=from_atlassian_console
JIRA_CLIENT_SECRET=from_atlassian_console
JIRA_CLOUD_ID=from_jira_settings
ACTION_SERVER_HOST=0.0.0.0
ACTION_SERVER_PORT=8000
```

#### OAuth Flow Diagram

```
User                                    Glean                    Atlassian
 │                                        │
 │ 1. Click authorize                  │
 ├───────────────────────────────────────────▶│
 │                                        │ 2. Redirect to
 │                                        ├──────────────────────────▶│
 │                                        │ 3. User authorizes
 │                                        │◀───────────│
 │ 4. Call your backend to exchange token │
 │◀──────────────────────────────────────│
 │                                        │ 5. Exchange code for token
 │                                        ├──────────────────────────▶│
 │                                        │ 6. Return access token
 │                                        │◀───────────────────│
 │                                        │
 └────────────────────────────────────────┴────────────────────┘
```

#### Key Points

- **Client URL** and **Authorization URL** are always Atlassian's URLs - never your server
- Your server address appears in **two places**:
  - **Atlassian Console**: As Callback URL (e.g., `https://jql.company.com/auth/callback`)
  - **Glean Admin UI**: As Action Endpoint (e.g., `https://jql.company.com/convert_to_jql`)
- Glean doesn't need to know your Callback URL - that's only for Atlassian
- The Action Endpoint is what Glean calls when users use your action

### Example Queries

| Natural Language | Generated JQL |
|-----------------|----------------|
| "Find all high priority bugs" | `priority = "Highest" AND issuetype = "Bug"` |
| "Show me open issues assigned to me" | `status = "Open" AND assignee = currentUser()` |
| "Find bugs created last week" | `issuetype = "Bug" AND created >= -7d` |
| "List all stories in project PROJ" | `project = PROJ AND issuetype = "Story"` |


实现总结

  已成功实现 Glean Action Server，用于将自然语言转换为有效的 Jira JQL 查询。

  创建的文件

  | 文件                      | 说明                          |
  |---------------------------|-------------------------------|
  | actions/__init__.py       | Package 初始化文件            |
  | actions/server.py         | FastAPI Web 服务器（~280 行） |
  | actions/jql_converter.py  | NL → JQL 转换服务（~230 行）  |
  | actions/jql_validator.py  | JQL 验证服务（~200 行）       |
  | actions/openapi_spec.yaml | OpenAPI 规范（Glean 集成）    |
  | prompts/jql_conversion.py | JQL 转换提示词模板（~250 行） |

  修改的文件

  | 文件             | 修改内容                                 |
  |------------------|------------------------------------------|
  | config/config.py | 添加 JiraConfig 和 ActionServerConfig 类 |
  | main.py          | 添加 action-server 命令入口              |
  | requirements.txt | 添加 FastAPI、Uvicorn、OAuth 依赖        |
  | .env.example     | 添加 Jira OAuth 和服务器配置变量         |

  核心功能

  1. JQL 转换服务 (jql_converter.py)
    - 使用 Glean Chat API 进行 NL → JQL 转换
    - 支持Few-Shot 学习
    - JSON 和文本两种输出格式解析
    - 基本语法验证
  2. JQL 验证服务 (jql_validator.py)
    - 调用 Jira REST API /search?validateQuery=true
    - OAuth 2.0 认证
    - 错误消息解析和建议生成
    - 重试机制
  3. FastAPI 服务器 (server.py)
    - POST /convert_to_jql - 主要端点
    - GET /health - 健康检查
    - GET /config - 配置信息
    - 完整的错误处理和日志

  使用方法

  # 1. 安装新依赖
  pip install -r requirements.txt

  # 2. 配置环境变量（复制 .env.example 到 .env 并编辑）
  cp .env.example .env
  # 编辑 .env 填入 Jira OAuth 配置

  # 3. 启动服务器
  python main.py action-server

  # 4. 访问 API 文档
  # http://localhost:8000/docs

  Glean 集成配置

  在 Glean Admin UI 配置 Action 时，使用以下 OAuth 设置：
  - Client URL: https://auth.atlassian.com/authorize?audience={ATLASSIAN_DOMAIN}.atlassian.net&prompt=consent
  - Authorization URL: https://auth.atlassian.com/oauth/token
  - Scopes: read:jira-work, read:jira-user, offline_access


  OAuth 流程中的 URL 角色

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                     OAuth 2.0 授权流程                          │
  │                                                               │
  │  用户                                    Glean                Atlassian     │
  │   │                                        │                    │           │
  │   │ 1. 点击授权                               │                    │           │
  │   ├───────────────────────────────────────────────────▶│                    │           │
  │   │                                        │ 2. 重定向到         │           │
  │   │                                        ├──────────────────────────▶│           │
  │   │                                        │                    │ 3. 用户登录/授权│
  │   │                                        │                    │◀───────────│
  │   │                                        │ 4. 带授权码返回      │           │
  │   │                                        │◀───────────────────│           │
  │   │ 5. 调用你的后端交换 Token                 │                    │           │
  │   │◀──────────────────────────────────────────────│                    │           │
  │   │                                        │ 6. 用授权码换 Token  │           │
  │   │                                        ├──────────────────────────▶│           │
  │   │                                        │                    │ 7. 返回 Token │
  │   │                                        │◀───────────────────│           │
  │   │                                        │                    │           │
  └──┴────────────────────────────────────────────────┴────────────────────┘

  三个关键 URL 的区别

  | URL                          | 属于谁             | 包含 Action URL？ | 说明                    |
  |------------------------------|--------------------|-------------------|-------------------------|
  | Client URL (授权 URL)        | Atlassian          | ❌ 不包含         | 用户登录授权的地方      |
  | Authorization URL (令牌 URL) | Atlassian          | ❌ 不包含         | 用授权码换 Token 的 API |
  | Callback URL (回调 URL)      | 你的 Action Server | ✅ 包含           | 授权后跳回的地方        |

  ---
  实际配置示例

  Glean Admin UI 配置（固定值）

  # 这些是 Atlassian 的固定 URL，不会包含你的服务器地址
  OAuth Config:
    Client URL: https://auth.atlassian.com/authorize?audience=your-company.atlassian.net&prompt=consent
    Authorization URL: https://auth.atlassian.com/oauth/token
    Scopes: read:jira-work, read:jira-user, offline_access

  Atlassian Developer Console 配置（需要你的 Callback URL）

  这是在 Atlassian Developer Console 中配置的：

  ┌──────────────────────────────────────────────────────────────┐
  │  Atlassian Developer Console - Create OAuth App           │
  │                                                      │
  │  App Name: Glean JQL Action                            │
  │                                                      │
  │  Callback URLs:              ← 这里填你的服务器地址！       │
  │    ✅ http://localhost:8000/auth/callback  (开发)         │
  │    ✅ https://jql.company.com/auth/callback (生产)        │
  │                                                      │
  │  [Save App]                                             │
  └──────────────────────────────────────────────────────────────┘

  ---
  关键理解

  Client URL 永远是 Atlassian 的 URL

  # Client URL（Glean Admin UI 显示）
  https://auth.atlassian.com/authorize?audience=your-company.atlassian.net&prompt=consent
                                      ^^^^^^^^^^^^^^
                                      这个是你的域名
                                      但整个URL是Atlassian的

  你的 Action Server URL 在哪里配置

  | 配置位置          | 配置项                  | 示例值                                 |
  |-------------------|-------------------------|----------------------------------------|
  | Glean Admin UI    | Action Endpoint         | https://jql.company.com/convert_to_jql |
  | Atlassian Console | Callback URL            | https://jql.company.com/auth/callback  |
  | 代码中            | ACTION_SERVER_HOST/PORT | 0.0.0.0:8000                           |

  ---
  完整 OAuth 配置清单

  1. Atlassian Developer Console（先做这个）

  创建 OAuth App:
  ├─ App Name: Glean JQL Action
  ├─ Callback URL: https://your-server.com/auth/callback  ← 你的服务器
  ├─ Scopes: read:jira-work, read:jira-user
  └─ 保存后获得:
      ├─ Client ID
      └─ Client Secret

  2. Glean Admin UI（然后配置这个）

  配置 Action:
  ├─ Action Type: Execution
  ├─ Action Endpoint: https://your-server.com/convert_to_jql  ← 你的服务器
  ├─ OpenAPI Spec: 上传 openapi_spec.yaml
  └─ OAuth (固定值):
      ├─ Client URL: https://auth.atlassian.com/authorize?...  ← Atlassian
      ├─ Authorization URL: https://auth.atlassian.com/oauth/token  ← Atlassian
      └─ Scopes: read:jira-work, read:jira-user, offline_access

  3. 你的 .env 文件

  ATLASSIAN_DOMAIN=your-company
  JIRA_CLIENT_ID=从Atlassian获得的ID
  JIRA_CLIENT_SECRET=从Atlassian获得的Secret
  JIRA_CLOUD_ID=从Jira获得的CloudID
  ACTION_SERVER_HOST=0.0.0.0
  ACTION_SERVER_PORT=8000

  ---
  总结：Client URL 和 Authorization URL 是 Atlassian 的固定地址，不包含你的服务器信息。你的服务器地址需要在 Atlassian Developer Console 中配置为 Callback URL，同时在 Glean Admin UI 中配置为 Action Endpoint。