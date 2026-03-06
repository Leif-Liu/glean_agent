"""
Glean Chat API 封装 - 使用 Glean 内置的 LLM 能力
"""
from typing import Dict, List, Any, Optional, AsyncIterator
from loguru import logger
from glean.api_client import Glean, models
from config.config import glean_config


class GleanChatWrapper:
    """
    Glean Chat API 封装

    功能：
    - 直接使用 Glean Chat API 进行问答
    - 无需外部 LLM 服务
    - 自动搜索和权限管理
    - 支持流式和非流式响应
    """

    def __init__(self):
        """初始化 Chat 封装"""
        self.client: Optional[Glean] = None
        logger.info("💬 Glean Chat Wrapper initialized")

    def _get_client(self) -> Glean:
        """获取 Glean 客户端"""
        if self.client is None:
            self.client = Glean(
                instance=glean_config.instance,
                api_token=glean_config.client_api_token
            )
        return self.client

    def ask(
        self,
        question: str,
        context: Optional[str] = None,
        stream: bool = False,
        timeout_millis: int = 30000,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        同步提问

        Args:
            question: 用户问题
            context: 上下文信息（可选）
            stream: 是否流式返回
            timeout_millis: 超时时间（毫秒）
            filters: 搜索过滤器

        Returns:
            回答响应
        """
        logger.info(f"💬 Asking Glean: {question[:50]}...")

        client = self._get_client()

        try:
            # 构建消息
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(text=question)]
                )
            ]

            # 添加上下文
            if context:
                messages.insert(0, models.ChatMessage(
                    fragments=[models.ChatMessageFragment(
                        text=f"上下文信息：\n{context}"
                    )]
                ))

            # 构建请求选项
            request_options = None
            if filters:
                request_options = models.ChatRequestOptions(
                    facet_filters=[
                        models.FacetFilter(
                            field_name=field_name,
                            values=[
                                models.FacetFilterValue(
                                    value=v,
                                    relation_type=models.RelationType.EQUALS
                                )
                                for v in (values if isinstance(values, list) else [values])
                            ]
                        )
                        for field_name, values in filters.items()
                    ]
                )

            # 调用 Chat API
            response = client.client.chat.create(
                messages=messages,
                timeout_millis=timeout_millis,
                request_options=request_options
            )

            logger.success(f"✅ Glean Chat response received")

            return {
                "success": True,
                "answer": response.text if hasattr(response, 'text') else str(response),
                "sources": self._extract_sources(response),
                "raw_response": response
            }

        except Exception as e:
            logger.error(f"❌ Glean Chat failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e)
            }

    async def ask_async(
        self,
        question: str,
        context: Optional[str] = None,
        stream: bool = False,
        timeout_millis: int = 30000,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步提问

        Args:
            question: 用户问题
            context: 上下文信息（可选）
            stream: 是否流式返回
            timeout_millis: 超时时间（毫秒）
            filters: 搜索过滤器

        Returns:
            回答响应
        """
        logger.info(f"💬 Asking Glean (async): {question[:50]}...")

        client = self._get_client()

        try:
            # 构建消息
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(text=question)]
                )
            ]

            # 添加上下文
            if context:
                messages.insert(0, models.ChatMessage(
                    fragments=[models.ChatMessageFragment(
                        text=f"上下文信息：\n{context}"
                    )]
                ))

            # 构建请求选项
            request_options = None
            if filters:
                request_options = models.ChatRequestOptions(
                    facet_filters=[
                        models.FacetFilter(
                            field_name=field_name,
                            values=[
                                models.FacetFilterValue(
                                    value=v,
                                    relation_type=models.RelationType.EQUALS
                                )
                                for v in (values if isinstance(values, list) else [values])
                            ]
                        )
                        for field_name, values in filters.items()
                    ]
                )

            # 调用异步 Chat API
            response = await client.client.chat.create_async(
                messages=messages,
                timeout_millis=timeout_millis,
                request_options=request_options
            )

            logger.success(f"✅ Glean Chat response received")

            return {
                "success": True,
                "answer": response.text if hasattr(response, 'text') else str(response),
                "sources": self._extract_sources(response),
                "raw_response": response
            }

        except Exception as e:
            logger.error(f"❌ Glean Chat failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e)
            }

    def ask_with_sources(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于指定来源提问

        Args:
            question: 用户问题
            sources: 来源文档列表
            context: 上下文信息

        Returns:
            回答响应
        """
        logger.info(f"💬 Asking Glean with {len(sources)} sources")

        client = self._get_client()

        try:
            # 构建包含来源的上下文
            source_context = self._build_source_context(sources)

            full_context = source_context
            if context:
                full_context = f"{context}\n\n{source_context}"

            # 构建消息
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(
                        text=f"基于以下信息回答问题：\n\n{full_context}\n\n问题：{question}"
                    )]
                )
            ]

            # 调用 Chat API
            response = client.client.chat.create(
                messages=messages,
                timeout_millis=60000  # 给予更多时间处理长上下文
            )

            logger.success(f"✅ Glean Chat with sources completed")

            return {
                "success": True,
                "answer": response.text if hasattr(response, 'text') else str(response),
                "raw_response": response
            }

        except Exception as e:
            logger.error(f"❌ Glean Chat with sources failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e)
            }

    def _build_source_context(self, sources: List[Dict[str, Any]]) -> str:
        """构建来源上下文字符串"""
        if not sources:
            return ""

        context_lines = ["以下是参考信息：\n"]
        for idx, source in enumerate(sources[:5], 1):  # 限制为5个来源
            title = source.get("title", "N/A")
            content = source.get("content", "")
            datasource = source.get("datasource", "N/A")
            url = source.get("url", "")

            context_lines.append(f"\n【来源 {idx}】{title}")
            context_lines.append(f"数据源：{datasource}")
            if url:
                context_lines.append(f"链接：{url}")
            context_lines.append(f"内容：{content[:500]}...")  # 限制每个来源500字

        return "\n".join(context_lines)

    def _extract_sources(self, response) -> List[Dict[str, Any]]:
        """从响应中提取来源信息"""
        sources = []

        # Chat API 响应可能包含来源引用
        if hasattr(response, 'citations') or hasattr(response, 'cites'):
            citations = getattr(response, 'citations', None) or getattr(response, 'cites', [])
            for citation in citations:
                if hasattr(citation, 'document'):
                    doc = citation.document
                    sources.append({
                        "title": getattr(doc, 'title', ''),
                        "url": getattr(doc, 'url', ''),
                        "datasource": getattr(doc, 'datasource', '')
                    })

        return sources

    def close(self):
        """关闭客户端连接"""
        if self.client:
            # Glean SDK 的客户端使用 context manager 自动管理
            self.client = None
            logger.debug("💬 Glean Chat Wrapper closed")


class GleanAgentsWrapper:
    """
    Glean Agents API 封装

    使用 Glean Agent Builder 创建的自定义 Agent
    适用于需要复杂工作流的场景
    """

    def __init__(self):
        """初始化 Agents 封装"""
        self.client: Optional[Glean] = None
        logger.info("🤖 Glean Agents Wrapper initialized")

    def _get_client(self) -> Glean:
        """获取 Glean 客户端"""
        if self.client is None:
            self.client = Glean(
                instance=glean_config.instance,
                api_token=glean_config.client_api_token
            )
        return self.client

    def search_agents(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索可用的 Agent

        Args:
            query: 搜索关键词

        Returns:
            Agent 列表
        """
        logger.info(f"🔍 Searching agents: {query}")

        client = self._get_client()

        try:
            response = client.client.agents.search(query=query)

            agents = []
            for agent in getattr(response, 'data', response):
                agents.append({
                    "id": getattr(agent, 'id', ''),
                    "name": getattr(agent, 'name', ''),
                    "description": getattr(agent, 'description', ''),
                    "created_by": getattr(agent, 'created_by', '')
                })

            logger.info(f"✅ Found {len(agents)} agents")
            return agents

        except Exception as e:
            logger.error(f"❌ Failed to search agents: {str(e)}")
            return []

    def run_agent(
        self,
        agent_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        运行指定的 Agent（同步）

        Args:
            agent_id: Agent ID（从 Agent Builder URL 中获取）
            query: 用户查询

        Returns:
            Agent 执行结果
        """
        logger.info(f"🤖 Running agent {agent_id}: {query[:50]}...")

        client = self._get_client()

        try:
            response = client.client.agents.run(
                agent_id=agent_id,
                messages=[{"role": "USER", "content": query}],
            )

            logger.success(f"✅ Agent {agent_id} completed")

            return {
                "success": True,
                "answer": str(response),
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"❌ Agent {agent_id} failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e),
            }

    async def run_agent_async(
        self,
        agent_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        异步运行指定的 Agent

        Args:
            agent_id: Agent ID
            query: 用户查询

        Returns:
            Agent 执行结果
        """
        logger.info(f"🤖 Running agent {agent_id} (async): {query[:50]}...")

        client = self._get_client()

        try:
            response = await client.client.agents.run_async(
                agent_id=agent_id,
                messages=[{"role": "USER", "content": query}],
            )

            logger.success(f"✅ Agent {agent_id} completed")

            return {
                "success": True,
                "answer": str(response),
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"❌ Agent {agent_id} failed: {str(e)}")
            return {
                "success": False,
                "answer": "",
                "error": str(e),
            }

    def get_agent_schemas(self, agent_id: str) -> Dict[str, Any]:
        """
        获取 Agent 的输入/输出 Schema

        Args:
            agent_id: Agent ID

        Returns:
            Schema 信息
        """
        logger.info(f"📋 Getting agent schemas: {agent_id}")

        client = self._get_client()

        try:
            response = client.client.agents.retrieve_schemas(agent_id=agent_id)

            return {
                "success": True,
                "agent_id": agent_id,
                "schemas": getattr(response, 'data', response)
            }

        except Exception as e:
            logger.error(f"❌ Failed to get agent schemas: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def close(self):
        """关闭客户端连接"""
        if self.client:
            self.client = None
            logger.debug("🤖 Glean Agents Wrapper closed")
