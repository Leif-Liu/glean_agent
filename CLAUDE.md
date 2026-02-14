# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Glean AI Agent is an intelligent enterprise knowledge assistant built on the Glean API. It performs question decomposition, deep analysis, intelligent search, and comprehensive summarization. The codebase is in Python (~5,000 lines) and follows a pipeline architecture with distinct phases for analysis, planning, execution, and synthesis.

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
