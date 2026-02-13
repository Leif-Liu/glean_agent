"""
内容总结器 - 生成准确、有证据的回答
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from config.config import agent_config


class ContentSummarizer:
    """
    内容总结器
    
    功能：
    - 多文档综合总结
    - 关键点提取
    - 证据链构建
    - 置信度评分
    - 格式化输出
    """
    
    def __init__(self):
        """初始化总结器"""
        logger.info("💡 Content Summarizer initialized")
    
    def generate_answer(
        self,
        question: str,
        analysis: Dict[str, Any],
        plan: Dict[str, Any],
        sources: List[Dict[str, Any]],
        execution_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成最终答案
        
        Args:
            question: 原始问题
            analysis: 问题分析结果
            plan: 执行计划
            sources: 检索到的文档来源
            execution_steps: 执行步骤
            
        Returns:
            包含内容、置信度、格式的答案
        """
        logger.info(f"💡 Generating answer for: {question[:50]}...")
        
        # 过滤有效的来源
        valid_sources = self._filter_valid_sources(sources)
        
        if not valid_sources:
            logger.warning("⚠️ No valid sources found")
            return self._generate_no_answer(question, analysis)
        
        # 提取关键信息
        key_points = self._extract_key_points(valid_sources, question)
        
        # 构建证据链
        evidence_chain = self._build_evidence_chain(valid_sources, question)
        
        # 生成总结内容
        content = self._generate_summary_content(
            question,
            key_points,
            evidence_chain,
            analysis,
            valid_sources
        )
        
        # 计算置信度
        confidence = self._calculate_confidence(
            valid_sources,
            evidence_chain,
            analysis
        )
        
        # 确定输出格式
        answer_format = self._determine_format(question, analysis)
        
        logger.success(f"✅ Answer generated (confidence: {confidence:.2f})")
        
        return {
            "content": content,
            "confidence": confidence,
            "format": answer_format,
            "sources_count": len(valid_sources),
            "key_points_count": len(key_points),
            "metadata": {
                "question_type": analysis.get("type"),
                "complexity": str(analysis.get("complexity")),
                "has_expertise": analysis.get("requires_expertise", False)
            }
        }
    
    def _filter_valid_sources(
        self,
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤有效的文档来源
        
        标准：
        - 有内容
        - 内容长度足够
        - 有标题或URL
        """
        valid = []
        
        for source in sources:
            # 检查是否有内容
            content = source.get("content", "")
            if not content or len(content) < 50:
                continue
            
            # 检查内容长度
            content_length = source.get("content_length", len(content))
            if content_length < 50:
                continue
            
            # 检查是否有标题或URL
            if not source.get("title") and not source.get("url"):
                continue
            
            valid.append(source)
        
        logger.debug(f"🔍 Filtered sources: {len(sources)} -> {len(valid)}")
        return valid
    
    def _generate_no_answer(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成"无答案"响应
        """
        content = f"抱歉，我没有找到足够的信息来回答您的问题：{question}\n\n"
        content += "建议：\n"
        content += "1. 尝试重新表述问题\n"
        content += "2. 使用更具体的关键词\n"
        content += "3. 如果问题涉及最新信息，请指定时间范围"
        
        return {
            "content": content,
            "confidence": 0.0,
            "format": "text",
            "sources_count": 0,
            "key_points_count": 0,
            "metadata": {
                "reason": "no_valid_sources"
            }
        }
    
    def _extract_key_points(
        self,
        sources: List[Dict[str, Any]],
        question: str
    ) -> List[Dict[str, Any]]:
        """
        从来源中提取关键点
        
        策略：
        - 识别与问题相关的句子/段落
        - 提取关键信息
        - 按相关性排序
        """
        key_points = []
        question_lower = question.lower()
        
        for source in sources:
            content = source.get("content", "")
            title = source.get("title", "")
            
            # 简化的关键点提取
            # 实际可以使用 NLP 模型或 LLM
            
            # 分段
            paragraphs = content.split("\n\n")
            
            for para in paragraphs:
                para = para.strip()
                if len(para) < 20:
                    continue
                
                # 检查是否与问题相关
                relevance = self._calculate_paragraph_relevance(
                    para,
                    question_lower,
                    title
                )
                
                if relevance > 0.3:  # 相关性阈值
                    key_points.append({
                        "content": para[:500],  # 限制长度
                        "source_title": title,
                        "source_url": source.get("url", ""),
                        "relevance": relevance,
                        "datasource": source.get("datasource", "")
                    })
            
            # 限制关键点数量
            if len(key_points) >= 10:
                break
        
        # 按相关性排序
        key_points.sort(key=lambda x: x["relevance"], reverse=True)
        
        # 返回前N个关键点
        return key_points[:5]
    
    def _calculate_paragraph_relevance(
        self,
        paragraph: str,
        question_lower: str,
        title: str
    ) -> float:
        """
        计算段落与问题的相关性
        
        简化实现：关键词匹配
        """
        para_lower = paragraph.lower()
        title_lower = title.lower()
        
        # 提取问题中的关键词（去停用词）
        question_words = set(
            word for word in question_lower.split()
            if len(word) > 2
        )
        
        if not question_words:
            return 0.0
        
        # 计算关键词匹配度
        matched_words = 0
        for word in question_words:
            if word in para_lower or word in title_lower:
                matched_words += 1
        
        relevance = matched_words / len(question_words)
        
        # 标题匹配加分
        if any(word in title_lower for word in question_words):
            relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _build_evidence_chain(
        self,
        sources: List[Dict[str, Any]],
        question: str
    ) -> List[Dict[str, Any]]:
        """
        构建证据链
        
        策略：
        - 识别相互支持的观点
        - 标记矛盾信息
        - 按来源组织
        """
        evidence_chain = []
        
        for source in sources:
            content = source.get("content", "")
            title = source.get("title", "")
            url = source.get("url", "")
            datasource = source.get("datasource", "")
            
            # 简化的证据提取
            # 实际可以使用 NLP 或 LLM
            
            # 提取前3段作为证据
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            evidence_chain.append({
                "source": {
                    "title": title,
                    "url": url,
                    "datasource": datasource
                },
                "evidence": paragraphs[:3],  # 最多3段证据
                "evidence_count": min(len(paragraphs), 3),
                "content_length": len(content)
            })
        
        return evidence_chain
    
    def _generate_summary_content(
        self,
        question: str,
        key_points: List[Dict[str, Any]],
        evidence_chain: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        生成总结内容
        
        策略：
        - 结构化输出
        - 引用证据
        - 标注来源
        """
        question_type = analysis.get("type", "general")
        
        # 生成标题
        content = f"## 回答：{question}\n\n"
        
        # 生成总结段落
        if key_points:
            content += "### 关键信息\n\n"
            for idx, point in enumerate(key_points, 1):
                content += f"{idx}. {point['content']}\n"
                content += f"   来源：{point['source_title']} ({point['datasource']})\n\n"
        
        # 添加证据部分
        if evidence_chain:
            content += "### 详细证据\n\n"
            for idx, evidence in enumerate(evidence_chain[:3], 1):  # 最多3个来源
                content += f"**来源 {idx}：{evidence['source']['title']}**\n"
                content += f"- 数据源：{evidence['source']['datasource']}\n"
                if evidence['source']['url']:
                    content += f"- 链接：{evidence['source']['url']}\n"
                
                # 添加证据内容
                if evidence['evidence']:
                    content += "- 关键内容：\n"
                    for para in evidence['evidence'][:2]:  # 最多2段
                        content += f"  - {para[:200]}...\n"
                
                content += "\n"
        
        # 根据问题类型添加特殊格式
        if question_type == "comparison":
            content += self._format_comparison(key_points, evidence_chain)
        elif question_type == "process":
            content += self._format_process(key_points, evidence_chain)
        
        # 添加来源列表
        if sources:
            content += "### 来源列表\n\n"
            for idx, source in enumerate(sources, 1):
                content += f"{idx}. {source.get('title', 'Unknown')}\n"
                content += f"   - 数据源：{source.get('datasource', 'Unknown')}\n"
                if source.get('url'):
                    content += f"   - 链接：{source['url']}\n"
                content += "\n"
        
        return content
    
    def _format_comparison(
        self,
        key_points: List[Dict[str, Any]],
        evidence_chain: List[Dict[str, Any]]
    ) -> str:
        """格式化对比类答案"""
        content = "\n### 对比分析\n\n"
        
        # 简化实现：直接返回关键点
        for point in key_points:
            content += f"- {point['content']}\n"
        
        return content + "\n"
    
    def _format_process(
        self,
        key_points: List[Dict[str, Any]],
        evidence_chain: List[Dict[str, Any]]
    ) -> str:
        """格式化流程类答案"""
        content = "\n### 步骤说明\n\n"
        
        # 简化实现：按步骤列出
        for idx, point in enumerate(key_points, 1):
            content += f"步骤 {idx}：{point['content']}\n"
        
        return content + "\n"
    
    def _calculate_confidence(
        self,
        sources: List[Dict[str, Any]],
        evidence_chain: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> float:
        """
        计算答案的置信度
        
        因素：
        - 来源数量
        - 内容质量
        - 来源多样性
        - 信息一致性
        """
        if not sources:
            return 0.0
        
        # 基础分数：基于来源数量
        base_score = min(len(sources) / 5.0, 1.0) * 0.4
        
        # 数据源多样性
        datasources = set(s.get("datasource", "") for s in sources)
        diversity_score = min(len(datasources) / 3.0, 1.0) * 0.2
        
        # 内容质量
        avg_content_length = sum(
            s.get("content_length", len(s.get("content", "")))
            for s in sources
        ) / len(sources)
        quality_score = min(avg_content_length / 500.0, 1.0) * 0.2
        
        # 信息一致性（简化）
        consistency_score = 0.2  # 默认认为一致
        
        confidence = base_score + diversity_score + quality_score + consistency_score
        
        return min(confidence, 1.0)
    
    def _determine_format(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> str:
        """
        确定答案的输出格式
        
        返回：text, markdown, structured
        """
        # 默认使用 markdown
        return "markdown"
