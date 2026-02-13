"""
响应生成模块 - 格式化和优化最终响应
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from config.config import agent_config


class ResponseBuilder:
    """
    响应构建器
    
    功能：
    - 格式化最终答案
    - 添加元数据
    - 优化输出结构
    - 生成不同格式的响应
    """
    
    def __init__(self):
        """初始化响应构建器"""
        self.include_sources = agent_config.include_sources
        self.include_confidence = agent_config.include_confidence
        self.include_execution_plan = agent_config.include_execution_plan
        
        logger.info("📨 Response Builder initialized")
    
    def build_response(
        self,
        query_result: Dict[str, Any],
        format_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        构建最终响应
        
        Args:
            query_result: 查询执行结果
            format_type: 格式类型（standard, compact, detailed）
            
        Returns:
            格式化的响应对象
        """
        logger.debug(f"📨 Building response (format: {format_type})")
        
        # 基础响应结构
        response = {
            "question": query_result.get("question"),
            "answer": query_result.get("answer"),
            "timestamp": query_result.get("timestamp")
        }
        
        # 添加置信度
        if self.include_confidence and "confidence" in query_result:
            response["confidence"] = query_result["confidence"]
        
        # 添加来源
        if self.include_sources and "sources" in query_result:
            response["sources"] = self._format_sources(
                query_result["sources"],
                format_type
            )
        
        # 添加执行计划
        if self.include_execution_plan and "plan" in query_result:
            response["execution_plan"] = self._format_plan(
                query_result["plan"],
                format_type
            )
        
        # 添加元数据
        response["metadata"] = self._build_metadata(query_result)
        
        # 根据格式类型调整结构
        if format_type == "compact":
            response = self._make_compact(response)
        elif format_type == "detailed":
            response = self._make_detailed(response)
        
        logger.debug(f"✅ Response built (length: {len(str(response))})")
        
        return response
    
    def _format_sources(
        self,
        sources: List[Dict[str, Any]],
        format_type: str
    ) -> List[Dict[str, Any]]:
        """
        格式化来源列表
        
        根据格式类型选择不同的详细程度
        """
        if format_type == "compact":
            # 紧凑格式：只包含标题和URL
            return [
                {
                    "title": s.get("title", "Unknown"),
                    "url": s.get("url", "")
                }
                for s in sources[:5]  # 最多5个来源
            ]
        elif format_type == "detailed":
            # 详细格式：包含所有元数据
            return [
                {
                    "title": s.get("title", "Unknown"),
                    "url": s.get("url", ""),
                    "datasource": s.get("datasource", "Unknown"),
                    "last_modified": s.get("last_modified", ""),
                    "content_length": s.get("content_length", 0)
                }
                for s in sources
            ]
        else:
            # 标准格式：标题、URL、数据源
            return [
                {
                    "title": s.get("title", "Unknown"),
                    "url": s.get("url", ""),
                    "datasource": s.get("datasource", "Unknown")
                }
                for s in sources
            ]
    
    def _format_plan(
        self,
        plan: Dict[str, Any],
        format_type: str
    ) -> Dict[str, Any]:
        """
        格式化执行计划
        """
        if format_type == "compact":
            # 紧凑格式：只包含步骤数量和策略
            return {
                "steps_count": len(plan.get("steps", [])),
                "strategy": plan.get("strategy", ""),
                "complexity": plan.get("complexity", "")
            }
        else:
            # 标准/详细格式：包含所有步骤
            return {
                "strategy": plan.get("strategy", ""),
                "complexity": plan.get("complexity", ""),
                "estimated_time": plan.get("estimated_time", ""),
                "steps": [
                    {
                        "step_id": step.get("step_id"),
                        "type": step.get("type"),
                        "description": step.get("description")
                    }
                    for step in plan.get("steps", [])
                ]
            }
    
    def _build_metadata(
        self,
        query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建响应元数据
        """
        metadata = {
            "execution_time": query_result.get("metadata", {}).get("execution_time", 0),
            "total_searches": query_result.get("metadata", {}).get("total_searches", 0),
            "documents_retrieved": query_result.get("metadata", {}).get("documents_retrieved", 0)
        }
        
        # 添加分析信息（如果有）
        if "analysis" in query_result:
            analysis = query_result["analysis"]
            metadata["question_analysis"] = {
                "type": analysis.get("type"),
                "complexity": str(analysis.get("complexity")),
                "entities_count": len(analysis.get("entities", []))
            }
        
        # 添加成功标志
        metadata["success"] = "error" not in query_result
        
        return metadata
    
    def _make_compact(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成紧凑格式的响应
        """
        return {
            "question": response["question"],
            "answer": response["answer"][:500] + "..." if len(response["answer"]) > 500 else response["answer"],
            "sources_count": len(response.get("sources", [])),
            "confidence": response.get("confidence", 0)
        }
    
    def _make_detailed(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成详细格式的响应
        """
        # 添加执行步骤详情
        if "execution_plan" not in response:
            return response
        
        detailed = response.copy()
        
        # 添加执行日志（如果存在）
        if "execution_log" in response:
            detailed["execution_log"] = response["execution_log"]
        
        return detailed
    
    def format_as_text(
        self,
        response: Dict[str, Any]
    ) -> str:
        """
        格式化为纯文本响应
        
        适用于聊天界面、命令行等
        """
        lines = []
        
        # 问题
        lines.append(f"问题：{response['question']}")
        lines.append("")
        
        # 答案
        lines.append("答案：")
        lines.append(response.get("answer", "无法生成答案"))
        lines.append("")
        
        # 置信度
        if "confidence" in response:
            confidence = response["confidence"]
            lines.append(f"置信度：{confidence:.2%}")
            lines.append("")
        
        # 来源
        if "sources" in response and response["sources"]:
            lines.append("来源：")
            for idx, source in enumerate(response["sources"], 1):
                lines.append(f"{idx}. {source.get('title', 'Unknown')}")
                if source.get("url"):
                    lines.append(f"   {source['url']}")
            lines.append("")
        
        # 元数据
        metadata = response.get("metadata", {})
        lines.append("元数据：")
        lines.append(f"- 执行时间：{metadata.get('execution_time', 0):.2f}秒")
        lines.append(f"- 搜索次数：{metadata.get('total_searches', 0)}")
        lines.append(f"- 检索文档：{metadata.get('documents_retrieved', 0)}")
        
        return "\n".join(lines)
    
    def format_as_markdown(
        self,
        response: Dict[str, Any]
    ) -> str:
        """
        格式化为 Markdown 响应
        
        适用于文档、网页等
        """
        lines = []
        
        # 标题
        lines.append(f"# {response['question']}")
        lines.append("")
        
        # 答案
        lines.append("## 答案")
        lines.append("")
        lines.append(response.get("answer", "无法生成答案"))
        lines.append("")
        
        # 置信度
        if "confidence" in response:
            confidence = response["confidence"]
            lines.append(f"**置信度**：{confidence:.2%}")
            lines.append("")
        
        # 来源
        if "sources" in response and response["sources"]:
            lines.append("## 来源")
            lines.append("")
            for idx, source in enumerate(response["sources"], 1):
                lines.append(f"{idx}. **{source.get('title', 'Unknown')}**")
                if source.get("datasource"):
                    lines.append(f"   - 数据源：{source['datasource']}")
                if source.get("url"):
                    lines.append(f"   - 链接：{source['url']}")
                lines.append("")
        
        # 元数据
        metadata = response.get("metadata", {})
        lines.append("## 元数据")
        lines.append("")
        lines.append(f"- **执行时间**：{metadata.get('execution_time', 0):.2f}秒")
        lines.append(f"- **搜索次数**：{metadata.get('total_searches', 0)}")
        lines.append(f"- **检索文档**：{metadata.get('documents_retrieved', 0)}")
        
        return "\n".join(lines)
