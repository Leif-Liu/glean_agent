"""
查询构建模块 - 构建优化的搜索查询
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from config.config import search_strategy


class QueryBuilder:
    """
    查询构建器
    
    功能：
    - 优化原始查询
    - 添加过滤条件
    - 构建高级查询
    - 查询扩展
    - 针对特定数据源优化
    """
    
    def __init__(self):
        """初始化查询构建器"""
        self.enable_expansion = search_strategy.enable_query_expansion
        self.expansion_terms = search_strategy.expansion_terms_count
        self.default_time_filter = search_strategy.default_time_filter
        
        logger.info("🔨 Query Builder initialized")
    
    def build_query(
        self,
        original_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建优化后的搜索查询
        
        Args:
            original_query: 原始查询
            context: 上下文信息（实体、类型等）
            
        Returns:
            包含查询、过滤器、排序等的完整查询对象
        """
        logger.debug(f"🔨 Building query for: {original_query}")
        
        # 解析原始查询
        parsed_query = self._parse_query(original_query)
        
        # 优化查询
        optimized_query = self._optimize_query(parsed_query, context)
        
        # 添加过滤器
        filters = self._build_filters(context)
        
        # 添加排序
        sort = self._build_sort(context)
        
        # 构建完整查询对象
        query_obj = {
            "query": optimized_query,
            "original_query": original_query,
            "filters": filters,
            "sort": sort,
            "metadata": {
                "optimized": True,
                "expansion_used": self.enable_expansion,
                "entities": context.get("entities", []) if context else []
            }
        }
        
        logger.debug(f"✅ Query built: {optimized_query}")
        
        return query_obj
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """
        解析原始查询
        
        提取：
        - 关键词
        - 引用词
        - 排除词
        - 布尔操作符
        """
        # 简化实现
        return {
            "raw": query,
            "keywords": query.split(),
            "quoted": self._extract_quoted(query),
            "excluded": self._extract_excluded(query)
        }
    
    def _extract_quoted(self, query: str) -> List[str]:
        """提取引用词"""
        import re
        return re.findall(r'"([^"]*)"', query)
    
    def _extract_excluded(self, query: str) -> List[str]:
        """提取排除词"""
        import re
        return re.findall(r'-(\w+)', query)
    
    def _optimize_query(
        self,
        parsed_query: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        优化查询
        
        策略：
        - 移除停用词
        - 添加相关术语
        - 调整词序
        """
        original = parsed_query["raw"]
        
        # 如果启用查询扩展
        if self.enable_expansion and context:
            entities = context.get("entities", [])
            if entities:
                # 添加前几个实体
                for entity in entities[:2]:
                    original = f"{original} {entity}"
        
        return original
    
    def _build_filters(
        self,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建过滤器
        
        基于上下文添加：
        - 时间过滤器
        - 数据源过滤器
        - 对象类型过滤器
        """
        filters = {}
        
        if not context:
            return filters
        
        # 时间过滤器
        if context.get("requires_recent_info"):
            filters["timeRange"] = self.default_time_filter
        
        # 数据源过滤器
        datasources = context.get("datasources", [])
        if datasources:
            filters["datasources"] = datasources
        
        # 对象类型过滤器
        object_types = context.get("object_types", [])
        if object_types:
            filters["objectTypes"] = object_types
        
        return filters
    
    def _build_sort(
        self,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建排序规则
        
        默认：按相关性排序
        """
        if context and context.get("requires_recent_info"):
            return {
                "field": "lastModified",
                "order": "DESC"
            }
        
        return {
            "field": "relevance",
            "order": "DESC"
        }
    
    def expand_query(
        self,
        query: str,
        terms: List[str]
    ) -> List[str]:
        """
        扩展查询
        
        生成多个查询变体
        """
        expanded = [query]
        
        for term in terms[:self.expansion_terms]:
            expanded.append(f"{query} {term}")
        
        return expanded
    
    def build_facet_filter(
        self,
        facet_name: str,
        values: List[str],
        relation_type: str = "EQUALS"
    ) -> Dict[str, Any]:
        """
        构建单个 Facet 过滤器
        
        Args:
            facet_name: Facet 名称
            values: 值列表
            relation_type: 关系类型（EQUALS, CONTAINS等）
            
        Returns:
            Facet 过滤器对象
        """
        return {
            "facetName": facet_name,
            "values": [
                {"relationType": relation_type, "value": v}
                for v in values
            ]
        }
    
    def build_time_filter(
        self,
        time_range: str = "past_month"
    ) -> Dict[str, str]:
        """
        构建时间过滤器
        
        Args:
            time_range: 时间范围（past_day, past_week, past_month, past_year）
            
        Returns:
            时间过滤器对象
        """
        return {
            "timeRange": time_range
        }
