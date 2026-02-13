"""
文档检索器 - 获取完整文档内容
"""
import asyncio
import requests
from typing import Dict, List, Any, Optional
from loguru import logger

from config.config import glean_config, agent_config
from utils.retry import clean_html


class DocumentRetriever:
    """
    文档检索器 - 增强版本
    
    功能：
    - 支持通过 HTTP 请求获取文档内容
    - 支持通过 Glean API 获取文档内容
    - 智能选择最佳获取策略
    - 清理和格式化内容
    - 处理不同文档类型和权限
    """
    
    def __init__(self, use_glean_api: bool = False):
        """
        初始化检索器
        
        Args:
            use_glean_api: 是否优先使用 Glean API 获取文档内容
        """
        self.use_glean_api = use_glean_api
        self.client = None
        self.retrieval_stats = {
            "http_retrievals": 0,
            "glean_api_retrievals": 0,
            "failed_retrievals": 0,
            "total_content_bytes": 0
        }
        
        logger.info(f"📄 Document Retriever initialized (glean_api: {use_glean_api})")
    
    def _get_glean_client(self):
        """获取 Glean 客户端（懒加载）"""
        if self.client is None and self.use_glean_api:
            try:
                from glean.api_client import Glean
                self.client = Glean(
                    instance=glean_config.instance,
                    api_token=glean_config.client_api_token
                )
                logger.info("🔌 Glean API client initialized")
            except ImportError:
                logger.warning("⚠️ Glean client not available, falling back to HTTP")
                self.use_glean_api = False
            except Exception as e:
                logger.error(f"❌ Failed to initialize Glean client: {str(e)}")
                self.use_glean_api = False
        
        return self.client
    
    async def retrieve_documents(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检索文档完整内容 - 增强实现
        
        策略：
        1. Glean API - 如果启用且有文档ID
        2. HTTP请求 - 如果有URL
        3. 失败处理 - 返回原始结果
        
        Args:
            search_results: 搜索结果列表
            
        Returns:
            包含完整内容的文档列表
        """
        if not search_results:
            return []
        
        logger.info(f"📄 Retrieving {len(search_results)} documents")
        
        # 并行处理文档检索
        tasks = []
        for result in search_results:
            task = self._retrieve_single_document(result)
            tasks.append(task)
        
        # 等待所有任务完成
        documents = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        retrieved = []
        for doc_result in documents:
            if isinstance(doc_result, Exception):
                logger.error(f"❌ Document retrieval exception: {str(doc_result)}")
                continue
            
            if doc_result:
                retrieved.append(doc_result)
        
        # 更新统计信息
        success_count = len([d for d in retrieved if d.get("content_length", 0) > 0])
        logger.info(f"✅ Retrieved {success_count}/{len(search_results)} documents successfully")
        
        return retrieved
    
    async def _retrieve_single_document(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        检索单个文档的完整内容
        
        策略选择：
        1. Glean API - 对于企业内部文档系统
        2. HTTP - 对于公开可访问的URL
        3. None - 无法获取
        """
        doc_id = result.get("id")
        url = result.get("url")
        datasource = result.get("datasource", "")
        
        # 智能选择获取策略
        retrieval_method = self._choose_retrieval_method(doc_id, url, datasource)
        
        try:
            if retrieval_method == "glean_api":
                content = await self._fetch_via_glean_api(doc_id, result)
                self.retrieval_stats["glean_api_retrievals"] += 1
            elif retrieval_method == "http":
                content = await self._fetch_via_http(url, result)
                self.retrieval_stats["http_retrievals"] += 1
            else:
                logger.warning(f"⚠️ No viable retrieval method for document {doc_id}")
                self.retrieval_stats["failed_retrievals"] += 1
                return self._create_fallback_result(result, "No viable retrieval method")
            
            # 清理和处理内容
            cleaned_content = clean_html(content)
            
            # 更新统计信息
            self.retrieval_stats["total_content_bytes"] += len(cleaned_content)
            
            # 返回完整结果
            return {
                **result,
                "content": cleaned_content,
                "content_length": len(cleaned_content),
                "retrieval_method": retrieval_method,
                "retrieved_at": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve document {doc_id}: {str(e)}")
            self.retrieval_stats["failed_retrievals"] += 1
            return self._create_fallback_result(result, str(e))
    
    def _choose_retrieval_method(self, doc_id: str, url: str, datasource: str) -> str:
        """
        智能选择最佳检索方法
        
        优先级：
        1. Glean API - 对于企业内部文档系统
        2. HTTP - 对于公开可访问的URL
        3. None - 无法选择
        """
        # 如果启用 Glean API 且有文档ID，优先使用
        if self.use_glean_api and doc_id:
            return "glean_api"
        
        # 如果有URL，使用HTTP
        if url:
            return "http"
        
        # 无法选择
        return None
    
    async def _fetch_via_glean_api(self, doc_id: str, search_result: Dict[str, Any]) -> str:
        """
        通过 Glean API 获取文档内容
        
        优势：
        - 内部系统访问权限
        - 获取完整结构化内容
        - 避免网页解析问题
        """
        client = self._get_glean_client()
        if not client:
            raise Exception("Glean API client not available")
        
        logger.debug(f"🔌 Fetching via Glean API: {doc_id}")
        
        # 使用 Glean API 获取文档内容
        # 根据文档类型使用不同的 API 端点
        try:
            # 这里根据不同的文档类型调用相应的 API
            # 例如：对于 Confluence 文档，使用 documents endpoint
            # 对于其他类型，可能需要使用不同的方法
            
            # 临时实现：假设有一个通用的文档获取方法
            response = client.documents.get_document(doc_id)
            
            # 解析响应内容
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'body'):
                return response.body
            else:
                # 回退到URL方法
                url = search_result.get("url")
                if url:
                    logger.debug(f"🔄 Glean API fell back to URL: {url}")
                    return await self._fetch_via_http(url, search_result)
                else:
                    raise Exception("No content available from Glean API")
                    
        except Exception as e:
            logger.warning(f"⚠️ Glean API failed, falling back to HTTP: {str(e)}")
            # 自动回退到HTTP方法
            url = search_result.get("url")
            if url:
                return await self._fetch_via_http(url, search_result)
            else:
                raise e
    
    async def _fetch_via_http(self, url: str, search_result: Dict[str, Any]) -> str:
        """
        通过 HTTP 请求获取文档内容
        
        特性：
        - 自动重试
        - 超时处理
        - User-Agent 设置
        - 错误处理
        """
        logger.debug(f"🌐 Fetching via HTTP: {url}")
        
        headers = {
            'User-Agent': 'Glean-AI-Agent/1.0 (Document Retrieval)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        try:
            # 在线程池中执行同步的 HTTP 请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    url,
                    headers=headers,
                    timeout=agent_config.search_timeout,
                    allow_redirects=True
                )
            )
            response.raise_for_status()
            
            # 检查内容长度限制
            content = response.text
            max_length = agent_config.max_content_length
            
            if len(content) > max_length:
                logger.warning(f"⚠️ Content too long ({len(content)} chars), truncating to {max_length}")
                content = content[:max_length]
            
            return content
            
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout while fetching {url}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed for {url}: {str(e)}")
    
    def _create_fallback_result(self, result: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """
        创建失败时的回退结果
        """
        return {
            **result,
            "content": "",
            "content_length": 0,
            "retrieval_error": error_msg,
            "retrieval_method": "failed",
            "retrieved_at": asyncio.get_event_loop().time()
        }
    
    def get_retrieval_statistics(self) -> Dict[str, Any]:
        """
        获取文档检索统计信息
        
        Returns:
            包含各种检索统计的字典
        """
        total = (self.retrieval_stats["http_retrievals"] + 
                self.retrieval_stats["glean_api_retrievals"] + 
                self.retrieval_stats["failed_retrievals"])
        
        return {
            **self.retrieval_stats,
            "total_retrievals": total,
            "success_rate": (self.retrieval_stats["http_retrievals"] + 
                          self.retrieval_stats["glean_api_retrievals"]) / max(total, 1),
            "glean_api_usage_ratio": self.retrieval_stats["glean_api_retrievals"] / max(total, 1),
            "average_content_size": self.retrieval_stats["total_content_bytes"] / max(
                self.retrieval_stats["http_retrievals"] + self.retrieval_stats["glean_api_retrievals"], 1
            )
        }
