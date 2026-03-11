"""
Glean AI Agent 配置管理
"""
import os
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from enum import Enum

load_dotenv()

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SearchMode(str, Enum):
    BASIC = "basic"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    DEEP = "deep"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class GleanConfig(BaseModel):
    """Glean API 配置"""
    
    # 基础配置
    instance: str = Field(default_factory=lambda: os.getenv("GLEAN_INSTANCE", ""))
    client_api_token: str = Field(default_factory=lambda: os.getenv("GLEAN_CLIENT_API_TOKEN", ""))
    indexing_api_token: str = Field(default_factory=lambda: os.getenv("GLEAN_INDEXING_TOKEN", ""))
    
    # 可选：模拟其他用户
    act_as: Optional[str] = Field(default_factory=lambda: os.getenv("GLEAN_ACT_AS"))
    
    # API 端点
    @property
    def client_api_url(self) -> str:
        return f"https://{self.instance}-be.glean.com/rest/api/v1"
    
    @property
    def indexing_api_url(self) -> str:
        return f"https://{self.instance}-be.glean.com/api/index/v1"
    
    def validate(self) -> None:
        """验证配置"""
        if not self.instance:
            raise ValueError("GLEAN_INSTANCE is required")
        if not self.client_api_token:
            raise ValueError("GLEAN_CLIENT_API_TOKEN is required")
        if not self.indexing_api_token:
            raise ValueError("GLEAN_INDEXING_TOKEN is required")


class AgentConfig(BaseModel):
    """智能体配置"""
    
    # 搜索配置
    max_search_results: int = Field(default=10, ge=1, le=50)
    default_search_mode: SearchMode = Field(default=SearchMode.HYBRID)
    enable_deep_search: bool = Field(default=True)
    search_timeout: int = Field(default=30, ge=5, le=120)
    max_snippet_size: int = Field(default=400, ge=50, le=2000)
    search_timeout_millis: int = Field(default=30000, ge=1000, le=120000)
    
    # 分析配置
    complexity_thresholds: dict = Field(default={
        ComplexityLevel.SIMPLE: 2,      # 单一轮搜索
        ComplexityLevel.MODERATE: 3,   # 最多3轮搜索
        ComplexityLevel.COMPLEX: 5,       # 最多5轮搜索
        ComplexityLevel.VERY_COMPLEX: 7   # 最多7轮搜索
    })
    
    # 缓存配置
    enable_caching: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)  # 默认1小时
    
    # 并发配置
    max_concurrent_searches: int = Field(default=3, ge=1, le=10)
    
    # 内容配置
    max_content_length: int = Field(default=1000000, ge=10000, le=10000000)  # 最大1MB内容
    
    # 日志配置
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_to_file: bool = Field(default=True)
    log_file_path: str = Field(default="logs/agent.log")
    
    # 响应配置
    max_answer_length: int = Field(default=2000, ge=500, le=10000)
    include_sources: bool = Field(default=True)
    include_confidence: bool = Field(default=True)
    include_execution_plan: bool = Field(default=True)


class SearchStrategy(BaseModel):
    """搜索策略配置"""
    
    # 查询增强
    enable_query_expansion: bool = Field(default=True)
    expansion_terms_count: int = Field(default=5, ge=1, le=10)
    
    # 过滤器
    default_time_filter: str = Field(default="past_month")
    enable_faceted_search: bool = Field(default=True)
    
    # 排序
    default_sort: str = Field(default="relevance")
    enable_reranking: bool = Field(default=True)


class AnalysisConfig(BaseModel):
    """分析配置"""
    
    # 问题类型检测
    enable_type_detection: bool = Field(default=True)
    
    # 实体识别
    enable_entity_extraction: bool = Field(default=True)
    
    # 意图理解
    enable_intent_analysis: bool = Field(default=True)
    
    # 上下文窗口
    context_window_size: int = Field(default=3, ge=1, le=10)


class LLMConfig(BaseModel):
    """LLM 大模型配置"""
    
    # API 配置
    base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"))
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    
    # 模型配置
    model_name: str = Field(default_factory=lambda: os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"))
    
    # 上下文配置
    context_length: int = Field(default=4096, ge=1024, le=128000)
    max_tokens: int = Field(default=2048, ge=128, le=64000)
    
    # 生成配置
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=50, ge=1, le=100)
    
    # 响应格式
    response_format: str = Field(default="json_object")  # json_object, text
    
    # 性能配置
    timeout: int = Field(default=60, ge=10, le=600)
    max_retries: int = Field(default=3, ge=1, le=10)
    
    # API 版本（兼容 OpenAI API）
    api_version: str = Field(default="v1")
    
    @property
    def chat_endpoint(self) -> str:
        """聊天完成端点"""
        # 支持 vllm OpenAI 兼容 API
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/chat/completions"
    
    def validate(self) -> None:
        """验证 LLM 配置"""
        if not self.base_url:
            raise ValueError("LLM_BASE_URL is required")
        if not self.model_name:
            raise ValueError("LLM_MODEL_NAME is required")


class JiraConfig(BaseModel):
    """Jira API 配置 (用于 Action Server)"""

    # OAuth 配置
    atlassian_domain: str = Field(default_factory=lambda: os.getenv("ATLASSIAN_DOMAIN", ""))
    jira_client_id: str = Field(default_factory=lambda: os.getenv("JIRA_CLIENT_ID", ""))
    jira_client_secret: str = Field(default_factory=lambda: os.getenv("JIRA_CLIENT_SECRET", ""))
    jira_cloud_id: str = Field(default_factory=lambda: os.getenv("JIRA_CLOUD_ID", ""))

    # Jira API 端点
    @property
    def jira_api_url(self) -> str:
        return f"https://{self.atlassian_domain}.atlassian.net/rest/api/3"

    @property
    def jira_search_url(self) -> str:
        return f"{self.jira_api_url}/search"

    @property
    def atlassian_oauth_url(self) -> str:
        return "https://auth.atlassian.com/oauth/token"

    def validate(self) -> None:
        """验证 Jira 配置"""
        if not self.atlassian_domain:
            raise ValueError("ATLASSIAN_DOMAIN is required")
        if not self.jira_client_id:
            raise ValueError("JIRA_CLIENT_ID is required")
        if not self.jira_client_secret:
            raise ValueError("JIRA_CLIENT_SECRET is required")


class ActionServerConfig(BaseModel):
    """Action Server 配置"""

    # 服务器配置
    host: str = Field(default_factory=lambda: os.getenv("ACTION_SERVER_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("ACTION_SERVER_PORT", "8000")))

    # API 配置
    api_title: str = Field(default="Glean JQL Action Server")
    api_version: str = Field(default="1.0.0")

    # 日志配置
    log_level: str = Field(default_factory=lambda: os.getenv("ACTION_SERVER_LOG_LEVEL", "INFO"))

    # 重试配置
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)

    # 超时配置
    request_timeout: int = Field(default=30, ge=5, le=120)


# 全局配置实例
glean_config = GleanConfig()
agent_config = AgentConfig()
search_strategy = SearchStrategy()
analysis_config = AnalysisConfig()
llm_config = LLMConfig()
jira_config = JiraConfig()
action_server_config = ActionServerConfig()

# 验证配置
try:
    glean_config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")