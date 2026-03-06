"""
Glean Chat Agent - 使用 Glean 内置 Chat API 的简化智能体
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from glean.api_client import Glean, models
from config.config import glean_config, agent_config
from modules.glean_chat_wrapper import GleanChatWrapper, GleanAgentsWrapper
from modules.searcher import GleanSearcher
from modules.retriever import DocumentRetriever


class GleanChatAgent:
    """
    Glean Chat Agent - 使用 Glean 内置 Chat API

    优势：
    - 无需外部 LLM 服务
    - 自动搜索集成
    - 自动权限管理
    - 代码简洁
    """

    def __init__(self, use_agents: bool = False, agent_id: Optional[str] = None):
        """
        初始化智能体

        Args:
            use_agents: 是否使用 Agents API（需要已配置的 Agent）
            agent_id: 指定的 Agent ID（从 Glean Agent Builder 获取）
        """
        self.use_agents = use_agents
        self.agent_id = agent_id

        # Glean SDK 客户端（同步调用）
        self._glean_client: Optional[Glean] = None

        # 初始化组件
        self.chat_wrapper = GleanChatWrapper()
        self.agents_wrapper = GleanAgentsWrapper() if use_agents else None
        self.searcher = GleanSearcher()
        self.retriever = DocumentRetriever()

        # 会话历史
        self.conversation_history: List[Dict[str, str]] = []

        # 执行统计
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "total_searches": 0,
            "total_documents_retrieved": 0
        }

        logger.info(f"🚀 Glean Chat Agent initialized (agents: {use_agents}, agent_id: {agent_id})")

    def _get_client(self) -> Glean:
        """获取 Glean SDK 客户端（懒加载）"""
        if self._glean_client is None:
            self._glean_client = Glean(
                instance=glean_config.instance,
                api_token=glean_config.client_api_token,
            )
        return self._glean_client

    def query(self, question: str, with_context: bool = True) -> Dict[str, Any]:
        """
        主查询接口

        Args:
            question: 用户问题
            with_context: 是否先搜索相关文档作为上下文

        Returns:
            完整响应
        """
        logger.info(f"📝 New query: {question}")
        start_time = datetime.now()

        self.stats["total_queries"] += 1

        response = {
            "question": question,
            "timestamp": datetime.now().isoformat(),
            "answer": None,
            "sources": [],
            "search_results": [],
            "execution_time": 0,
            "success": False
        }

        try:
            if self.use_agents and self.agent_id:
                # 使用 Agents API
                logger.info("🤖 Using Glean Agents API")
                result = self._query_via_agents(question)
                response["answer"] = result.get("answer", "")
                response["success"] = result.get("success", False)
                if not result.get("success"):
                    response["error"] = result.get("error", "Unknown error")
            else:
                # 使用 Chat API
                logger.info("💬 Using Glean Chat API")

                if with_context:
                    # 通过 SDK 同步搜索相关文档
                    search_results = self._search_sync(question)
                    self.stats["total_searches"] += 1
                    response["search_results"] = search_results

                    if search_results:
                        # 将搜索结果的 snippet 作为来源上下文传给 Chat
                        sources = [
                            {
                                "title": r.get("title", ""),
                                "content": r.get("snippet", ""),
                                "datasource": r.get("datasource", ""),
                                "url": r.get("url", ""),
                            }
                            for r in search_results[:5]
                        ]
                        self.stats["total_documents_retrieved"] += len(sources)
                        response["sources"] = sources

                        result = self.chat_wrapper.ask_with_sources(
                            question=question,
                            sources=sources,
                        )
                        response["answer"] = result.get("answer", "")
                        response["success"] = result.get("success", False)
                    else:
                        result = self.chat_wrapper.ask(question=question)
                        response["answer"] = result.get("answer", "")
                        response["success"] = result.get("success", False)
                else:
                    # 直接提问（让 Glean 自动搜索）
                    result = self.chat_wrapper.ask(question=question)
                    response["answer"] = result.get("answer", "")
                    response["success"] = result.get("success", False)

                    if result.get("sources"):
                        response["sources"] = result["sources"]

            # 记录会话历史
            self.conversation_history.append({
                "question": question,
                "answer": response.get("answer", ""),
                "timestamp": datetime.now().isoformat()
            })

            # 限制历史长度
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            # 更新统计
            if response.get("success"):
                self.stats["successful_queries"] += 1

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            response["execution_time"] = round(execution_time, 2)

            logger.info(f"✅ Query completed in {execution_time:.2f}s")

        except Exception as e:
            logger.error(f"❌ Query failed: {str(e)}")
            response["error"] = str(e)
            response["success"] = False

        return response

    def _search_sync(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用 Glean SDK 同步搜索（glean.client.search.query）

        Args:
            question: 搜索查询
            filters: 可选 facet 过滤器 {field_name: [values]}

        Returns:
            标准化搜索结果列表
        """
        client = self._get_client()

        facet_filters = None
        if filters:
            facet_filters = [
                models.FacetFilter(
                    field_name=field_name,
                    values=[
                        models.FacetFilterValue(
                            value=v,
                            relation_type=models.RelationType.EQUALS,
                        )
                        for v in (values if isinstance(values, list) else [values])
                    ],
                )
                for field_name, values in filters.items()
            ]

        search_kwargs: Dict[str, Any] = {
            "query": question,
            "page_size": agent_config.max_search_results,
            "max_snippet_size": agent_config.max_snippet_size,
            "timeout_millis": agent_config.search_timeout_millis,
        }
        if facet_filters:
            search_kwargs["request_options"] = models.SearchRequestOptions(
                facet_filters=facet_filters,
            )

        try:
            res = client.client.search.query(**search_kwargs)
        except Exception as e:
            logger.error(f"❌ Sync search failed: {e}")
            return []

        return self._parse_search_response(res)

    @staticmethod
    def _parse_search_response(response) -> List[Dict[str, Any]]:
        """将 SDK SearchResponse 转换为标准化字典列表"""
        results_list = getattr(response, "results", None)
        if not results_list:
            return []

        parsed = []
        for result in results_list:
            parsed.append(GleanSearcher._extract_result_fields(result))
        return parsed

    def _query_via_agents(self, question: str) -> Dict[str, Any]:
        """通过 Agents API 查询"""
        if not self.agents_wrapper or not self.agent_id:
            return {
                "success": False,
                "answer": "",
                "error": "Agents not configured"
            }

        try:
            result = self.agents_wrapper.run_agent(
                agent_id=self.agent_id,
                query=question
            )
            return result
        except Exception as e:
            logger.error(f"❌ Agent query failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e)
            }

    def chat(
        self,
        message: str,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """
        对话接口（连续对话）

        Args:
            message: 用户消息
            include_history: 是否包含历史上下文

        Returns:
            对话响应
        """
        logger.info(f"💬 Chat message: {message[:50]}...")

        # 构建上下文
        context = None
        if include_history and self.conversation_history:
            recent_history = self.conversation_history[-3:]
            if recent_history:
                context_lines = ["最近的对话：\n"]
                for item in recent_history:
                    context_lines.append(f"Q: {item['question']}")
                    context_lines.append(f"A: {item['answer'][:100]}...")
                context = "\n".join(context_lines)

        # 调用 Chat API
        result = self.chat_wrapper.ask(
            question=message,
            context=context
        )

        # 记录到历史
        if result.get("success"):
            self.conversation_history.append({
                "question": message,
                "answer": result.get("answer", ""),
                "timestamp": datetime.now().isoformat()
            })

            # 限制历史长度
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            **self.stats,
            "conversation_length": len(self.conversation_history),
            "success_rate": (
                self.stats["successful_queries"] / max(self.stats["total_queries"], 1)
            )
        }

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        logger.info("🧹 Conversation history cleared")

    def search_available_agents(self, query: str = "") -> List[Dict[str, Any]]:
        """
        搜索可用的 Agents

        Args:
            query: 搜索关键词

        Returns:
            Agent 列表
        """
        if not self.agents_wrapper:
            logger.warning("⚠️ Agents wrapper not initialized")
            return []

        return self.agents_wrapper.search_agents(query=query)

    def set_agent(self, agent_id: str):
        """
        设置使用的 Agent

        Args:
            agent_id: Agent ID（从 Glean Agent Builder 获取）
        """
        self.agent_id = agent_id
        self.use_agents = True
        logger.info(f"🤖 Agent set to: {agent_id}")

    def disable_agents(self):
        """禁用 Agents，使用普通 Chat API"""
        self.use_agents = False
        logger.info("💬 Switched to plain Chat API (agents disabled)")

    def close(self):
        """关闭所有连接"""
        self.chat_wrapper.close()
        if self.agents_wrapper:
            self.agents_wrapper.close()
        self._glean_client = None
        logger.info("🔌 Glean Chat Agent closed")


# 便捷函数：创建不同配置的 Agent 实例
def create_simple_agent() -> GleanChatAgent:
    """创建简单 Agent（仅使用 Chat API，无上下文）"""
    return GleanChatAgent(use_agents=False)


def create_context_agent() -> GleanChatAgent:
    """创建上下文感知 Agent（搜索后 Chat）"""
    return GleanChatAgent(use_agents=False)


def create_agent_with_id(agent_id: str) -> GleanChatAgent:
    """创建使用指定 Agent 的 Agent"""
    return GleanChatAgent(use_agents=True, agent_id=agent_id)
