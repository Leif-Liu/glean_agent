"""
搜索模块 - Glean 搜索引擎（修正版）
"""
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

from glean.api_client import Glean, models
from glean.api_client.errors import GleanError
from config.config import (
    glean_config, agent_config, search_strategy
)
from utils.retry import retry_on_rate_limit


class GleanSearcher:
    """
    Glean 搜索引擎 - 修正版
    
    功能：
    - 多模式搜索（基础、语义、混合、深度）
    - 查询优化和扩展
    - 智能过滤
    - 结果缓存
    - 正确的 Glean API 调用
    """
    
    def __init__(self):
        """初始化搜索器"""
        self.client = None
        self._cache = {}
        self.query_count = 0
        
        logger.info("🔍 Glean Searcher initialized (corrected API calls)")
    
    def _get_client(self) -> Glean:
        """获取 Glean 客户端"""
        if self.client is None:
            self.client = Glean(
                instance=glean_config.instance,
                api_token=glean_config.client_api_token
            )
        return self.client
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            filters: 过滤器
            mode: 搜索模式（basic, semantic, hybrid, deep）
            
        Returns:
            搜索结果列表
        """
        self.query_count += 1
        cache_key = self._get_cache_key(query, filters, mode)
        
        # 检查缓存
        if agent_config.enable_caching and cache_key in self._cache:
            logger.debug(f"🔄 Cache hit: {cache_key}")
            return self._cache[cache_key]
        
        logger.info(f"🔍 Searching: {query} (mode: {mode})")
        
        try:
            @retry_on_rate_limit(max_retries=3)
            async def do_search():
                client = self._get_client()
                
                # 根据模式选择搜索策略
                if mode == "basic":
                    return await self._basic_search(client, query, filters)
                elif mode == "semantic":
                    return await self._semantic_search(client, query, filters)
                elif mode == "deep":
                    return await self._deep_search(client, query, filters)
                else:  # hybrid
                    return await self._hybrid_search(client, query, filters)
            
            results = await do_search()
            
            # 缓存结果
            if agent_config.enable_caching:
                self._cache[cache_key] = results
            
            logger.success(f"✅ Found {len(results)} results")
            return results
            
        except GleanError as e:
            logger.error(f"❌ Search failed (GleanError): {str(e)}")
            return []
        except Exception as e:
            logger.error(f"❌ Search failed (General): {str(e)}")
            return []
    
    async def _call_search_api(
        self,
        client: Glean,
        query: str,
        request_options: Optional[Dict[str, Any]]
    ) -> Any:
        """
        调用 Glean 搜索 API - 正确的官方 SDK 用法

        使用 client.client.search.query_async() 进行异步搜索

        Args:
            client: Glean 客户端
            query: 搜索查询
            request_options: 请求选项（可选）

        Returns:
            API 响应对象
        """
        try:
            logger.debug(f"📞 Calling client.client.search.query_async()")

            # 构建搜索请求参数
            search_params = {"query": query}

            # 如果提供了 request_options，转换为 SearchRequestOptions 模型
            if request_options:
                facet_filters_list = []
                if "facetFilters" in request_options:
                    for ff in request_options["facetFilters"]:
                        facet_filters_list.append(
                            models.FacetFilter(
                                field_name=ff["facetName"],
                                values=[
                                    models.FacetFilterValue(
                                        value=v["value"],
                                        relation_type=models.RelationType.EQUALS
                                    )
                                    for v in ff["values"]
                                ]
                            )
                        )

                search_params["request_options"] = models.SearchRequestOptions(
                    page_size=request_options.get("pageSize", agent_config.max_search_results),
                    facet_filters=facet_filters_list if facet_filters_list else None
                )
            else:
                search_params["page_size"] = agent_config.max_search_results

            # 使用异步方法调用
            response = await client.client.search.query(**search_params)

            logger.debug(f"✅ Search API call successful")
            return response

        except AttributeError as e:
            logger.error(f"❌ API method not found: {str(e)}")
            raise GleanError(f"Search API method not available: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Search API call failed: {str(e)}")
            raise
    
    async def _basic_search(
        self,
        client: Glean,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基础搜索"""
        logger.info("🔍 Basic search mode")

        # 构建搜索请求选项
        request_options = None

        # 添加过滤器
        if filters:
            request_options = {
                "facetFilters": self._build_facet_filters(filters)
            }

        try:
            # 调用统一的搜索接口
            response = await self._call_search_api(
                client,
                query,
                request_options
            )

            return self._parse_search_results(response)

        except GleanError:
            logger.error("❌ Basic search failed")
            return []
    
    async def _semantic_search(
        self,
        client: Glean,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """语义搜索（使用查询扩展）"""
        logger.info("🧠 Semantic search mode")

        # 扩展查询
        expanded_queries = self._expand_query(query)

        if not expanded_queries:
            # 如果没有扩展查询，回退到基础搜索
            logger.warning("⚠️ No expanded queries, falling back to basic search")
            return await self._basic_search(client, query, filters)

        all_results = []
        for expanded_query in expanded_queries:
            # 计算每个查询的页面大小
            page_size = max(agent_config.max_search_results // len(expanded_queries), 1)

            request_options = {
                "pageSize": page_size
            }

            if filters:
                request_options["facetFilters"] = self._build_facet_filters(filters)

            try:
                response = await self._call_search_api(
                    client,
                    expanded_query,
                    request_options
                )

                results = self._parse_search_results(response)
                all_results.extend(results)

            except GleanError as e:
                logger.warning(f"⚠️ Semantic search failed for '{expanded_query}': {str(e)}")
                continue

        # 去重和排序
        all_results = self._deduplicate_results(all_results)

        return all_results[:agent_config.max_search_results]
    
    async def _hybrid_search(
        self,
        client: Glean,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """混合搜索（基础 + 语义）"""
        logger.info("🔀 Hybrid search mode")
        
        # 并行执行基础和语义搜索
        tasks = [
            self._basic_search(client, query, filters),
            self._semantic_search(client, query, filters)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        basic_results = results[0] if not isinstance(results[0], Exception) else []
        semantic_results = results[1] if not isinstance(results[1], Exception) else []
        
        # 合并结果
        combined = basic_results + semantic_results
        
        # 去重
        deduplicated = self._deduplicate_results(combined)
        
        # 重新排序（基于相关性）
        reranked = self._rerank_results(deduplicated, query)
        
        return reranked[:agent_config.max_search_results]
    
    async def _deep_search(
        self,
        client: Glean,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """深度搜索（多轮迭代）"""
        logger.info("🔬 Deep search mode")
        
        all_results = []
        
        # 第一轮：主查询
        primary_results = await self._basic_search(client, query, filters)
        all_results.extend(primary_results)
        
        # 第二轮：基于实体搜索
        entities = self._extract_entities(query)
        for entity in entities[:3]:
            entity_results = await self._basic_search(
                client,
                f'"{entity}"',  # 精确匹配
                filters
            )
            all_results.extend(entity_results)
        
        # 第三轮：宽泛搜索
        broad_query = self._broaden_query(query)
        if broad_query != query:  # 只有当查询真的被宽泛化时才搜索
            broad_results = await self._basic_search(
                client,
                broad_query,
                filters
            )
            all_results.extend(broad_results)
        
        # 去重并返回
        deduplicated = self._deduplicate_results(all_results)
        
        return deduplicated[:agent_config.max_search_results * 2]  # 深度搜索返回更多结果
    
    def _expand_query(self, query: str) -> List[str]:
        """扩展查询"""
        expanded = [query]
        
        if search_strategy.enable_query_expansion:
            # 添加相关术语
            terms = self._get_related_terms(query)
            for term in terms[:search_strategy.expansion_terms_count]:
                expanded.append(f"{query} {term}")
        
        return expanded
    
    def _broaden_query(self, query: str) -> str:
        """宽泛化查询"""
        # 移除具体限定词
        query_lower = query.lower()
        broadened = query
        
        modifiers = ["current", "new", "latest", "specific", "particular", "exact"]
        for modifier in modifiers:
            if modifier in query_lower:
                broadened = query_lower.replace(modifier, "").strip()
                break
        
        return broadened
    
    def _get_related_terms(self, query: str) -> List[str]:
        """获取相关术语"""
        # 简化实现
        # 实际可以使用词向量或知识库
        terms = {
            "政策": ["规定", "规则", "准则", "guidelines"],
            "流程": ["步骤", "方法", "procedure", "process"],
            "系统": ["平台", "工具", "software", "system"],
            "安全": ["合规", "风险", "security", "compliance"],
            "工作": ["employment", "work", "job", "career"]
        }
        
        # 查找相关术语
        for key, related in terms.items():
            if key in query:
                return related
        
        return []
    
    def _extract_entities(self, query: str) -> List[str]:
        """
        提取实体 - 改进版
        
        策略：
        - 提取3字以上的有意义词汇
        - 优先提取专有名词（首字母大写）
        - 识别技术术语
        - 不限制数量，返回所有识别的实体
        """
        import re
        
        # 基础实体提取（3字以上）
        entities = re.findall(r"[\w\u4e00-\u9fa5]{3,}", query)
        
        # 提取专业术语（缩写、连字符词等）
        technical_entities = re.findall(
            r"\b[A-Z]{2,}\b|"  # API, SSO等缩写
            r"\b[a-z]+(?:-[a-z]+)+\b|"  # multi-step等连字符词
            r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+",  # KnowledgeBase等驼峰词
            query
        )
        
        # 合并并去重
        all_entities = list(set(entities + technical_entities))
        
        # 按优先级排序（长词优先）
        all_entities.sort(key=lambda x: len(x), reverse=True)
        
        return all_entities
    
    def _build_facet_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建 Facet 过滤器 - 适配 SDK 格式"""
        facet_filters = []

        for field_name, values in filters.items():
            if isinstance(values, list):
                facet_filters.append({
                    "field_name": field_name,  # SDK 使用 snake_case
                    "values": [
                        {"relationType": "EQUALS", "value": v}
                        for v in values
                    ]
                })
            else:
                facet_filters.append({
                    "field_name": field_name,
                    "values": [
                        {"relationType": "EQUALS", "value": values}
                    ]
                })

        return facet_filters
    
    def _parse_search_results(self, response) -> List[Dict[str, Any]]:
        """
        解析搜索结果 - 兼容 Glean SDK 响应格式

        Args:
            response: API 响应对象

        Returns:
            解析后的结果列表
        """
        if response is None:
            logger.warning("⚠️ Response is None")
            return []

        try:
            # 检查响应对象的结构 - SDK 返回 SearchResponse 对象
            results_list = None

            if hasattr(response, 'results'):
                # SDK 返回格式：SearchResponse.results
                results_list = response.results
            elif hasattr(response, 'data'):
                if hasattr(response.data, 'results'):
                    results_list = response.data.results
                else:
                    results_list = response.data
            elif isinstance(response, list):
                results_list = response
            elif isinstance(response, dict):
                results_list = response.get('results') or response.get('data', [])

            if not results_list:
                return []

            parsed = []
            for result in results_list:
                # 兼容 SDK 返回的对象和字典两种格式
                if hasattr(result, '__dict__'):
                    # 对象格式
                    parsed.append({
                        "id": getattr(result, 'id', ''),
                        "title": getattr(result, 'title', ''),
                        "snippet": getattr(result, 'snippet', ''),
                        "url": getattr(result, 'url', ''),
                        "datasource": getattr(result, 'datasource', ''),
                        "last_modified": getattr(result, 'last_modified', ''),
                        "object_type": getattr(result, 'object_type', ''),
                        "metadata": getattr(result, 'metadata', {})
                    })
                else:
                    # 字典格式
                    parsed.append({
                        "id": result.get('id', ''),
                        "title": result.get('title', ''),
                        "snippet": result.get('snippet', ''),
                        "url": result.get('url', ''),
                        "datasource": result.get('datasource', ''),
                        "last_modified": result.get('last_modified', ''),
                        "object_type": result.get('object_type', ''),
                        "metadata": result.get('metadata', {})
                    })

            logger.debug(f"✅ Parsed {len(parsed)} results")
            return parsed

        except Exception as e:
            logger.error(f"❌ Failed to parse search results: {str(e)}")
            return []
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        seen_urls = set()
        deduplicated = []
        
        for result in results:
            url = result.get("url") or result.get("id", "")
            if url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(result)
        
        return deduplicated
    
    def _rerank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """重新排序结果"""
        # 简化实现：基于标题和片段匹配度
        query_terms = set(query.lower().split())
        
        for result in results:
            title_lower = result.get("title", "").lower()
            snippet_lower = result.get("snippet", "").lower()
            
            score = 0
            
            # 标题匹配
            for term in query_terms:
                if term in title_lower:
                    score += 3
                elif term in snippet_lower:
                    score += 1
            
            # 数据源优先级
            datasource = result.get("datasource", "")
            if datasource in ["confluence", "sharepoint"]:
                score += 2
            elif datasource in ["slack", "teams"]:
                score += 1
            
            # 时间新近度
            if search_strategy.default_time_filter:
                result["score"] = score
            else:
                result["score"] = score
        
        # 按分数排序
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
    def _get_cache_key(self, query: str, filters: Dict[str, Any], mode: str) -> str:
        """生成缓存键"""
        import hashlib
        cache_data = f"{query}:{str(sorted(filters.items()))}:{mode}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def clear_cache(self):
        """清空缓存"""
        self._cache = {}
        logger.info("🧹 Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "query_count": self.query_count,
            "cache_size": len(self._cache),
            "cache_hit_rate": self._get_cache_hit_rate()
        }
    
    def _get_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        # 简化实现
        # 实际需要跟踪缓存命中和未命中
        return 0.0