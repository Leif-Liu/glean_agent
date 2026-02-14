"""
Glean AI Agent - 核心智能体类（优化版：使用 Glean Chat API）
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from config.config import (
    glean_config, agent_config,
    ComplexityLevel, LogLevel
)
from glean.api_client import Glean, models
from core.planner import QuestionPlanner
from core.analyzer import QuestionAnalyzer
from core.orchestrator import TaskOrchestrator
from modules.searcher import GleanSearcher
from modules.retriever import DocumentRetriever
from modules.summarizer import ContentSummarizer


class GleanAI:
    """
    Glean AI 智能体主类（优化版）

    功能：
    - 问题分析：理解用户意图和复杂度
    - 问题分解：拆分复杂问题为子任务
    - 智能搜索：多策略并行搜索（Glean API）
    - 信息整合：去重、排序、验证
    - 综合总结：使用 Glean Chat API 生成准确、有证据的回答

    优化：
    - 使用 Glean Chat API 替代外部 LLM
    - 无需配置 LLM_BASE_URL
    - 简化代码复杂度
    """

    def __init__(self):
        """初始化智能体"""
        # 初始化组件
        self.analyzer = QuestionAnalyzer()
        self.planner = QuestionPlanner()
        self.searcher = GleanSearcher()
        self.retriever = DocumentRetriever()
        self.summarizer = ContentSummarizer()
        self.orchestrator = TaskOrchestrator()

        # Glean Chat API 客户端（用于替代外部 LLM）
        self.glean_chat_client: Optional[Glean] = None

        # 会话管理（用于对话历史）
        self.conversation_history: List[Dict[str, str]] = []

        # 执行状态
        self.execution_log: List[Dict[str, Any]] = []
        self.current_query: Optional[str] = None
        self.search_results: List[Dict[str, Any]] = []

        # 配置日志
        self._setup_logging()

        logger.info(f"🚀 Glean AI Agent initialized (optimized: using Glean Chat API)")

    def _get_glean_chat_client(self) -> Glean:
        """获取 Glean Chat 客户端"""
        if self.glean_chat_client is None:
            self.glean_chat_client = Glean(
                instance=glean_config.instance,
                api_token=glean_config.client_api_token
            )
        return self.glean_chat_client

    def _setup_logging(self):
        """配置日志"""
        import sys
        from pathlib import Path

        # 确保日志目录存在
        log_dir = Path(agent_config.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置 loguru
        logger.remove()  # 移除默认处理器
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
            level=agent_config.log_level.upper()
        )

        if agent_config.log_to_file:
            logger.add(
                agent_config.log_file_path,
                rotation="500 MB",
                level=agent_config.log_level.upper()
            )

    def query(self, question: str) -> Dict[str, Any]:
        """
        主查询接口

        Args:
            question: 用户问题

        Returns:
            包含分析、计划、执行和答案的完整响应
        """
        logger.info(f"📝 New query: {question}")
        start_time = time.time()

        self.current_query = question
        response = {
            "question": question,
            "timestamp": datetime.now().isoformat(),
            "analysis": None,
            "plan": None,
            "search_strategies": None,
            "execution_steps": [],
            "sources": [],
            "answer": None,
            "confidence": None,
            "metadata": {
                "execution_time": 0,
                "total_searches": 0,
                "documents_retrieved": 0
            }
        }

        try:
            # 阶段 1：问题分析
            logger.info("=" * 60)
            logger.info("🧠 PHASE 1: Question Analysis")
            logger.info("=" * 60)

            analysis = self.analyzer.analyze(question)
            response["analysis"] = analysis
            self._log_step("Question Analysis", analysis)

            # 阶段 2：问题分解
            logger.info("=" * 60)
            logger.info("🎯 PHASE 2: Question Decomposition")
            logger.info("=" * 60)

            plan = self.planner.decompose(question, analysis)
            response["plan"] = plan
            self._log_step("Decomposition", plan)

            # 阶段 3：执行计划
            logger.info("=" * 60)
            logger.info("🚀 PHASE 3: Execution")
            logger.info("=" * 60)

            results = asyncio.run(self._execute_plan(plan))
            response["execution_steps"] = results["steps"]
            response["sources"] = results["sources"]
            response["metadata"]["total_searches"] = results["total_searches"]
            response["metadata"]["documents_retrieved"] = results["documents_retrieved"]

            # 阶段 4：综合总结（使用 Glean Chat API）
            logger.info("=" * 60)
            logger.info("💬 PHASE 4: Synthesis (Glean Chat API)")
            logger.info("=" * 60)

            answer = await self._synthesize_via_glean_chat(
                question=question,
                analysis=analysis,
                sources=results["sources"],
                execution_steps=results["steps"]
            )

            response["answer"] = answer["content"]
            response["confidence"] = answer.get("confidence", None)
            response["answer_format"] = answer.get("format", "text")

            # 计算执行时间
            execution_time = time.time() - start_time
            response["metadata"]["execution_time"] = round(execution_time, 2)

            logger.info(f"✅ Query completed in {execution_time:.2f}s")
            logger.success(f"📊 Final Answer: {answer['content'][:200]}...")

        except Exception as e:
            logger.error(f"❌ Query failed: {str(e)}")
            response["error"] = str(e)
            response["success"] = False

        return response

    async def _execute_plan(
        self,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行分解的计划

        Args:
            plan: 从 planner 生成的执行计划

        Returns:
            执行结果，包括步骤、来源和统计信息
        """
        results = {
            "steps": [],
            "sources": [],
            "total_searches": 0,
            "documents_retrieved": 0
        }

        # 执行每个步骤
        for step_idx, step in enumerate(plan["steps"], 1):
            logger.info(f"\n📍 Executing Step {step_idx}/{len(plan['steps'])}: {step['description']}")

            step_result = await self._execute_step(step)

            # 记录步骤结果
            results["steps"].append({
                "step_number": step_idx,
                "description": step["description"],
                "type": step["type"],
                "result": step_result,
                "success": step_result.get("success", False)
            })

            # 聚合所有来源
            if "sources" in step_result:
                results["sources"].extend(step_result["sources"])
                results["documents_retrieved"] += len(step_result["sources"])

            results["total_searches"] += step_result.get("searches_performed", 0)

        # 去重来源
        results["sources"] = self._deduplicate_sources(results["sources"])

        return results

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step: 步骤定义

        Returns:
            步骤执行结果
        """
        step_type = step.get("type", "search")

        if step_type == "search":
            return await self._execute_search_step(step)
        elif step_type == "analyze":
            # 使用 Glean Chat API 替代外部 LLM
            return await self._execute_analyze_step_optimized(step)
        elif step_type == "synthesize":
            # 使用 Glean Chat API 替代外部 LLM
            return await self._execute_synthesize_step_optimized(step)
        else:
            logger.warning(f"⚠️  Unknown step type: {step_type}")
            return {"success": False, "error": f"Unknown step type: {step_type}"}

    async def _execute_search_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行搜索步骤（使用 Glean Search API）

        ✅ 已优化：使用 Glean API 调用
        """
        query = step["query"]
        filters = step.get("filters", {})
        search_mode = step.get("mode", agent_config.default_search_mode)

        logger.info(f"🔍 Search query: {query}")
        logger.info(f"📋 Filters: {filters}")
        logger.info(f"🎯 Mode: {search_mode}")

        try:
            # 执行搜索（通过 Glean API）
            search_results = await self.searcher.search(
                query=query,
                filters=filters,
                mode=search_mode
            )

            # 检索完整文档
            if search_results and len(search_results) > 0:
                retrieved_docs = await self.retriever.retrieve_documents(
                    search_results[:agent_config.max_search_results]
                )
            else:
                retrieved_docs = []

            logger.success(f"✅ Found {len(search_results)} results, retrieved {len(retrieved_docs)} documents")

            return {
                "success": True,
                "type": "search",
                "searches_performed": 1,
                "query": query,
                "results_count": len(search_results),
                "retrieved_count": len(retrieved_docs),
                "sources": retrieved_docs
            }

        except Exception as e:
            logger.error(f"❌ Search step failed: {str(e)}")
            return {
                "success": False,
                "type": "search",
                "error": str(e),
                "sources": []
            }

    async def _execute_analyze_step_optimized(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析步骤 - 使用 Glean Chat API（优化版）

        功能：
        - 交叉验证信息一致性
        - 识别矛盾或冲突点
        - 提取关键洞察
        - 评估信息可信度
        """
        logger.info(f"🔬 Analyzing: {step.get('description', 'Unknown')}")

        try:
            # 获取需要分析的数据
            sources = step.get("sources", [])
            context = step.get("context", "")

            if not sources:
                logger.warning("⚠️  No sources to analyze")
                return {
                    "success": False,
                    "type": "analyze",
                    "error": "No sources provided for analysis"
                }

            # 构建分析提示（使用 Glean Chat）
            analysis_prompt = self._build_analysis_prompt(
                context=context,
                sources=sources,
                analysis_type=step.get("analysis_type", "consistency")
            )

            # 使用 Glean Chat API 进行分析
            client = self._get_glean_chat_client()
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(text=analysis_prompt)]
                )
            ]

            response = await client.client.chat.create_async(
                messages=messages,
                timeout_millis=60000  # 给予更多时间处理分析任务
            )

            # 解析分析结果
            analysis_result = self._parse_analysis_result(
                response.text if hasattr(response, 'text') else str(response)
            )

            logger.success(f"✅ Analysis completed: {len(analysis_result.get('insights', []))} insights")

            return {
                "success": True,
                "type": "analyze",
                "analysis": {
                    "insights": analysis_result.get("insights", []),
                    "contradictions": analysis_result.get("contradictions", []),
                    "confidence_score": analysis_result.get("confidence_score", 0.0),
                    "key_findings": analysis_result.get("key_findings", [])
                }
            }

        except Exception as e:
            logger.error(f"❌ Analysis step failed: {str(e)}")
            return {
                "success": False,
                "type": "analyze",
                "error": str(e)
            }

    async def _execute_synthesize_step_optimized(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行综合步骤 - 使用 Glean Chat API（优化版）

        功能：
        - 整合多个来源的信息
        - 构建连贯的叙述
        - 识别支持/反对证据
        - 生成平衡的观点
        """
        logger.info(f"🔗 Synthesizing: {step.get('description', 'Unknown')}")

        try:
            # 获取需要综合的数据
            sources = step.get("sources", [])
            question = step.get("question", self.current_query)
            previous_analyses = step.get("previous_analyses", [])

            if not sources:
                logger.warning("⚠️  No sources to synthesize")
                return {
                    "success": False,
                    "type": "synthesize",
                    "error": "No sources provided for synthesis"
                }

            # 构建综合提示（使用 Glean Chat）
            synthesis_prompt = self._build_synthesis_prompt(
                question=question,
                sources=sources,
                previous_analyses=previous_analyses
            )

            # 使用 Glean Chat API 进行综合
            client = self._get_glean_chat_client()
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(text=synthesis_prompt)]
                )
            ]

            response = await client.client.chat.create_async(
                messages=messages,
                timeout_millis=60000  # 给予更多时间处理综合任务
            )

            # 解析综合结果
            synthesis_result = self._parse_synthesis_result(
                response.text if hasattr(response, 'text') else str(response)
            )

            logger.success(f"✅ Synthesis completed: {len(synthesis_result.get('key_points', []))} key points")

            return {
                "success": True,
                "type": "synthesize",
                "synthesis": {
                    "summary": synthesis_result.get("summary", ""),
                    "key_points": synthesis_result.get("key_points", []),
                    "supporting_evidence": synthesis_result.get("supporting_evidence", []),
                    "contradictions": synthesis_result.get("contradictions", []),
                    "sections": synthesis_result.get("sections", [])
                }
            }

        except Exception as e:
            logger.error(f"❌ Synthesis step failed: {str(e)}")
            return {
                "success": False,
                "type": "synthesize",
                "error": str(e)
            }

    def _build_analysis_prompt(self, context: str, sources: List[Dict[str, Any]], analysis_type: str) -> str:
        """构建分析提示词"""
        prompt = f"""任务：分析以下信息并提取洞察

上下文：{context}

分析类型：{analysis_type}

来源信息：
"""

        for idx, source in enumerate(sources[:5], 1):  # 限制为前5个来源
            prompt += f"""
来源 {idx}:
- 标题: {source.get('title', 'N/A')}
- 内容: {source.get('content', 'N/A')[:500]}...
- 来源: {source.get('datasource', 'N/A')}
"""

        prompt += """
请分析以上信息，并以以下格式返回：
## 关键洞察
（列出你发现的主要洞察，每条一行）

## 潜在矛盾
（如果发现任何不一致或矛盾信息）

## 信息可信度
（给出0-1之间的分数）

请以清晰的文本格式返回，不要使用 JSON。"""
        return prompt

    def _build_synthesis_prompt(self, question: str, sources: List[Dict[str, Any]], previous_analyses: List[Dict[str, Any]]) -> str:
        """构建综合提示词"""
        prompt = f"""任务：综合多个来源的信息，回答用户问题

用户问题：{question}

前序分析：
"""
        for idx, analysis in enumerate(previous_analyses, 1):
            prompt += f"""
分析 {idx}:
{analysis.get('description', 'N/A')}
"""

        prompt += f"""
来源信息（共{len(sources)}个）：
"""
        for idx, source in enumerate(sources[:8], 1):  # 限制为前8个来源
            prompt += f"""
来源 {idx}:
- 标题: {source.get('title', 'N/A')}
- 数据源: {source.get('datasource', 'N/A')}
- 关键内容: {source.get('content', 'N/A')[:400]}...
"""

        prompt += """
请综合以上信息，回答用户问题。请以以下格式返回：

## 主要回答
（直接回答用户问题）

## 关键点
（列出3-5个关键点）

## 支持证据
（引用相关的来源）

请以清晰的文本格式返回。"""
        return prompt

    def _parse_analysis_result(self, text: str) -> Dict[str, Any]:
        """解析分析结果"""
        result = {
            "insights": [],
            "contradictions": [],
            "confidence_score": 0.0,
            "key_findings": []
        }

        lines = text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('##'):
                current_section = line.replace('##', '').strip().lower()
            elif current_section == '关键洞察' or current_section == '关键洞察':
                result["insights"].append(line)
            elif current_section == '潜在矛盾' or current_section == '矛盾':
                result["contradictions"].append(line)
            elif '可信度' in line or '分数' in line:
                # 尝试提取数字分数
                import re
                match = re.search(r'(\d+\.?\d*)', line)
                if match:
                    try:
                        result["confidence_score"] = float(match.group(1))
                    except ValueError:
                        result["confidence_score"] = 0.5
            elif current_section == '主要发现' or current_section == '关键发现':
                result["key_findings"].append(line)

        # 如果没有提取到任何内容，返回默认值
        if not result["insights"] and not result["contradictions"]:
            result["insights"] = ["已分析提供的来源信息"]

        if result["confidence_score"] == 0.0:
            result["confidence_score"] = 0.5  # 默认中等置信度

        return result

    def _parse_synthesis_result(self, text: str) -> Dict[str, Any]:
        """解析综合结果"""
        result = {
            "summary": "",
            "key_points": [],
            "supporting_evidence": [],
            "contradictions": [],
            "sections": []
        }

        lines = text.split('\n')
        current_section = None
        current_section_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('##'):
                # 保存上一节内容
                if current_section and current_section_content:
                    if current_section == '主要回答' or current_section == '回答':
                        result["summary"] = '\n'.join(current_section_content)
                    elif current_section == '关键点':
                        result["key_points"] = current_section_content[:]
                        result["key_points"] = result["key_points"][:5]
                    elif current_section == '支持证据' or current_section == '证据':
                        result["supporting_evidence"] = current_section_content[:]
                    elif current_section == '潜在矛盾' or current_section == '矛盾':
                        result["contradictions"] = current_section_content[:]

                # 开始新节
                current_section = line.replace('##', '').strip().lower()
                current_section_content = []
            else:
                current_section_content.append(line)

        # 保存最后一节内容
        if current_section and current_section_content:
            if current_section == '主要回答' or current_section == '回答':
                result["summary"] = '\n'.join(current_section_content)
            elif current_section == '关键点':
                result["key_points"] = current_section_content[:]
                result["key_points"] = result["key_points"][:5]
            elif current_section == '支持证据' or current_section == '证据':
                result["supporting_evidence"] = current_section_content[:]
            elif current_section == '潜在矛盾' or current_section == '矛盾':
                result["contradictions"] = current_section_content[:]

        # 如果没有找到摘要，使用整个文本
        if not result["summary"]:
            result["summary"] = text[:2000]

        return result

    async def _synthesize_via_glean_chat(
        self,
        question: str,
        analysis: Dict[str, Any],
        sources: List[Dict[str, Any]],
        execution_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用 Glean Chat API 进行最终综合

        Args:
            question: 原始问题
            analysis: 问题分析结果
            sources: 检索到的文档来源
            execution_steps: 执行步骤

        Returns:
            包含内容、置信度、格式的答案
        """
        logger.info(f"💬 Synthesizing via Glean Chat: {question[:50]}...")

        # 过滤有效的来源
        valid_sources = self._filter_valid_sources(sources)

        if not valid_sources:
            logger.warning("⚠️  No valid sources found")
            return self._generate_no_answer(question, analysis)

        # 构建包含来源的上下文
        source_context = self._build_source_context(valid_sources)

        # 构建最终问题提示
        final_prompt = f"""基于以下信息回答问题：

用户问题：{question}

问题分析：{analysis.get('type', 'N/A')}，复杂度：{analysis.get('complexity', 'N/A')}

{source_context}

请提供：
1. 直接的回答
2. 支持的来源（按相关性排序）
3. 关键点总结
4. 如果有矛盾，请指出"""

        try:
            client = self._get_glean_chat_client()
            messages = [
                models.ChatMessage(
                    fragments=[models.ChatMessageFragment(text=final_prompt)]
                )
            ]

            response = await client.client.chat.create_async(
                messages=messages,
                timeout_millis=60000
            )

            # 提取答案内容
            answer_text = response.text if hasattr(response, 'text') else str(response)

            # 计算置信度
            confidence = self._calculate_confidence(
                valid_sources,
                answer_text
            )

            # 确定输出格式
            answer_format = self._determine_format(question, analysis)

            logger.success(f"✅ Answer generated (confidence: {confidence:.2f})")

            return {
                "content": answer_text,
                "confidence": confidence,
                "format": answer_format,
                "sources_count": len(valid_sources),
                "metadata": {
                    "question_type": analysis.get("type"),
                    "complexity": str(analysis.get("complexity", "N/A")),
                    "requires_expertise": analysis.get("requires_expertise", False)
                }
            }

        except Exception as e:
            logger.error(f"❌ Glean Chat synthesis failed: {str(e)}")
            return self._generate_no_answer(question, analysis)

    def _filter_valid_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤有效的文档来源"""
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

    def _generate_no_answer(self, question: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成"无答案"响应"""
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
            "metadata": {
                "reason": "no_valid_sources"
            }
        }

    def _build_source_context(self, sources: List[Dict[str, Any]]) -> str:
        """构建来源上下文字符串"""
        if not sources:
            return ""

        context_lines = ["相关来源信息：\n"]
        for idx, source in enumerate(sources[:5], 1):  # 限制为5个来源
            title = source.get("title", "N/A")
            content = source.get("content", "")
            datasource = source.get("datasource", "N/A")
            url = source.get("url", "")

            context_lines.append(f"{idx}. {title}")
            context_lines.append(f"   - 数据源：{datasource}")
            if url:
                context_lines.append(f"   - 链接：{url}")
            context_lines.append(f"   - 内容摘要：{content[:300]}...")

        return "\n".join(context_lines)

    def _calculate_confidence(self, sources: List[Dict[str, Any]], answer_text: str) -> float:
        """计算答案的置信度"""
        if not sources:
            return 0.0

        # 基于来源数量的基础分数
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

        # 答案长度（适当的长度表示更详细的回答）
        length_score = min(len(answer_text) / 500.0, 1.0) * 0.1

        confidence = base_score + diversity_score + quality_score + length_score

        return min(confidence, 1.0)

    def _determine_format(self, question: str, analysis: Dict[str, Any]) -> str:
        """确定答案的输出格式"""
        # 默认使用 markdown
        return "markdown"

    def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重文档来源"""
        if not sources:
            return []

        seen_urls = set()
        deduplicated = []

        for source in sources:
            url = source.get("url") or source.get("id", "")

            if url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(source)
            else:
                logger.debug(f"🔄 Duplicate source removed: {url}")

        logger.info(f"🔄 Deduplicated: {len(sources)} -> {len(deduplicated)} sources")
        return deduplicated

    def _log_step(self, phase: str, data: Dict[str, Any]):
        """记录步骤到日志"""
        log_entry = {
            "phase": phase,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        self.execution_log.append(log_entry)
        logger.debug(f"📊 Logged: {phase}")

    def get_execution_trace(self) -> Dict[str, Any]:
        """获取完整的执行追踪"""
        return {
            "query": self.current_query,
            "log": self.execution_log,
            "total_steps": len(self.execution_log),
            "timestamp": datetime.now().isoformat()
        }
