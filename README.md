# Glean AI Agent

基于 Glean API 的智能企业知识助手，具备问题分解、深度分析、智能搜索和综合总结能力。

## 功能特性

### 核心能力

- 🧠 **智能问题分析**
  - 识别问题类型
  - 提取关键实体
  - 判断复杂度等级
  - 确定所需搜索策略

- 🎯 **问题分解**
  - 将复杂问题拆分为子任务
  - 生成执行计划
  - 识别依赖关系
  - 优化搜索策略

- 🔍 **多维度搜索**
  - 语义搜索
  - 关键词搜索
  - 过滤器优化
  - 多数据源并行查询

- 📊 **信息整合**
  - 结果去重
  - 相关性排序
  - 交叉验证
  - 上下文构建

- 💡 **智能总结**
  - 多文档综合
  - 关键点提取
  - 证据链构建
  - 置信度评分

- 🔄 **迭代优化**
  - 结果评估
  - 查询重写
  - 深度扩展
  - 自我修正

## 项目结构

```
glean-agent/
├── config/              # 配置管理
│   └── config.py
├── core/               # 核心智能体逻辑
│   ├── agent.py        # 主智能体类
│   ├── planner.py      # 问题分解器
│   ├── analyzer.py     # 问题分析器
│   └── orchestrator.py # 任务协调器
├── modules/            # 功能模块
│   ├── indexer.py      # 文档索引
│   ├── searcher.py     # 搜索引擎
│   ├── retriever.py    # 检索器
│   └── summarizer.py   # 总结器
├── tools/              # 工具集
│   ├── data_source.py  # 数据源管理
│   ├── query_builder.py # 查询构建
│   └── response.py     # 响应生成
├── prompts/            # 提示模板
│   └── templates.py
├── tests/              # 测试套件
│   └── test_agent.py
├── requirements.txt
├── .env.example
└── README.md
```

## 安装

```bash
# 克隆或进入项目目录
cd glean-agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 Glean 配置
```

## 快速开始

```python
from core.agent import GleanAI

# 初始化智能体
agent = GleanAI()

# 回答问题
response = agent.query(
    "我们公司关于远程工作的政策是什么？需要注意什么事项？"
)

# 查看详细执行过程
print("=" * 60)
print("问题分析：", response["analysis"])
print("=" * 60)
print("执行计划：", response["plan"])
print("=" * 60)
print("搜索策略：", response["search_strategies"])
print("=" * 60)
print("最终答案：", response["answer"])
print("=" * 60)
print("来源文档：", response["sources"])
print("=" * 60)
print("执行日志：", response["execution_log"])
```

## 环境配置

```bash
# .env 文件
GLEAN_INSTANCE=your-company-instance
GLEAN_CLIENT_API_TOKEN=glean_abc123...
GLEAN_INDEXING_TOKEN=glean_xyz456...

# 可选配置
MAX_SEARCH_RESULTS=10
ENABLE_DEEP_SEARCH=true
USE_CACHING=true
LOG_LEVEL=debug
```

## API 集成

本项目集成了 Glean 的所有主要 API：

- ✅ **Indexing API** - 文档索引和管理
- ✅ **Search API** - 多维度搜索和过滤
- ✅ **Chat API** - 对话式问答
- ✅ **Agents API** - 预构建智能体执行
- ✅ **Activity API** - 用户活动跟踪

## 开发

```bash
# 运行测试
python -m pytest tests/

# 启动交互模式
python -m tools.interactive

# 查看日志
tail -f logs/agent.log
```

## 运行模式

### 原始模式（使用外部 LLM）

```bash
# 演示模式
python main.py demo

# 交互模式
python main.py interactive

# 单次查询
python main.py "你的问题"
```

### 优化模式（使用 Glean Chat API）✨

```bash
# 优化演示模式（无需外部 LLM）
python main.py glean-chat-demo

# 优化交互模式
python main.py glean-chat-interactive
```

**优势：**
- 无需配置外部 LLM 服务
- 自动利用 Glean 的搜索和 LLM 能力
- 自动继承 Glean 权限系统
- 更快的响应速度

### Glean Agents 模式

```bash
# 列出可用的 Agents
python main.py agents

# 使用特定 Agent 查询
python main.py agent <agent_id> "你的问题"
```

**Agent ID 获取：**
在 Glean Agent Builder 中创建 Agent 后，URL 中会显示：
`https://your-instance.glean.com/admin/agents/<agent_id>`

## 许可证

MIT License
