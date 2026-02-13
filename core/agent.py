"""
Glean AI Agent - 核心智能体类
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
import aiohttp

from config.config import (
    glean_config, agent_config, 
    ComplexityLevel, LogLevel, llm_config
)
from core.planner import QuestionPlanner
from core.analyzer import QuestionAnalyzer
from core.orchestrator import TaskOrchestrator
from modules.searcher import GleanSearcher
from modules.retriever import DocumentRetriever
from modules.summarizer import ContentSummarizer


class GleanAI:
    """
    Glean AI 智能体主类
    
    功能：
    - 问题分析：理解用户意图和复杂度
    - 问题分解：拆分复杂问题为子任务
    - 智能搜索：多策略并行搜索
    - 信息整合：去重、排序、验证
    - 综合总结：生成准确、有证据的回答
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
        
        # LLM 配置
        self.llm_config = llm_config
        self._validate_llm_config()
        
        # 会话管理（用于对话历史）
        self.conversation_history: List[Dict[str, str]] = []
        
        # HTTP 客户端（用于 LLM 调用）
        self._llm_session = None
        
        # 配置 TaskOrchestrator 的组件引用
        # 这样它可以使用默认执行器来执行真实的任务
        self.orchestrator.set_components(
            searcher=self.searcher,
            retriever=self.retriever,
            analyzer=self.analyzer,
            summarizer=self.summarizer
        )
        
        # 执行状态
        self.execution_log: List[Dict[str, Any]] = []
        self.current_query: Optional[str] = None
        self.search_results: List[Dict[str, Any]] = []
        
        # 配置日志
        self._setup_logging()
        
        logger.info(f"🚀 Glean AI Agent initialized")
        logger.info(f"🤖 LLM configured: {llm_config.model_name} @ {llm_config.base_url}")
    
    def _validate_llm_config(self):
        """验证 LLM 配置"""
        try:
            self.llm_config.validate()
            logger.info("✅ LLM configuration validated")
        except ValueError as e:
            logger.warning(f"⚠️  LLM config warning: {str(e)}")
            logger.warning("⚠️  LLM features will be disabled")
    
    async def _get_llm_session(self) -> aiohttp.ClientSession:
        """获取或创建 LLM HTTP 会话"""
        if self._llm_session is None or self._llm_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.llm_config.timeout)
            self._llm_session = aiohttp.ClientSession(timeout=timeout)
        return self._llm_session
    
    async def _close_llm_session(self):
        """关闭 LLM 会话"""
        if self._llm_session and not self._llm_session.closed:
            await self._llm_session.close()
            logger.debug("🔌 LLM session closed")
    
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
            
            # 阶段 4：综合总结
            logger.info("=" * 60)
            logger.info("💡 PHASE 4: Synthesis & Summarization")
            logger.info("=" * 60)
            
            answer = self.summarizer.generate_answer(
                question=question,
                analysis=analysis,
                plan=plan,
                sources=results["sources"],
                execution_steps=results["steps"]
            )
            
            response["answer"] = answer["content"]
            response["confidence"] = answer["confidence"]
            response["answer_format"] = answer["format"]
            
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
            return await self._execute_analyze_step(step)
        elif step_type == "synthesize":
            return await self._execute_synthesize_step(step)
        else:
            logger.warning(f"⚠️  Unknown step type: {step_type}")
            return {"success": False, "error": f"Unknown step type: {step_type}"}
    
    async def _execute_search_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行搜索步骤
        """
        query = step["query"]
        filters = step.get("filters", {})
        search_mode = step.get("mode", agent_config.default_search_mode)
        
        logger.info(f"🔍 Search query: {query}")
        logger.info(f"📋 Filters: {filters}")
        logger.info(f"🎯 Mode: {search_mode}")
        
        try:
            # 执行搜索
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
    
    async def _execute_analyze_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行分析步骤 - 使用大模型进行深度分析
        
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
                logger.warning("⚠️ No sources to analyze")
                return {
                    "success": False,
                    "type": "analyze",
                    "error": "No sources provided for analysis"
                }
            
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(
                context=context,
                sources=sources,
                analysis_type=step.get("analysis_type", "consistency")
            )
            
            # 使用 ContentSummarizer 的底层模型进行分析
            # 这里可以集成 LLM 调用
            analysis_result = await self._run_llm_analysis(analysis_prompt)
            
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
    
    def _build_analysis_prompt(
        self,
        context: str,
        sources: List[Dict[str, Any]],
        analysis_type: str
    ) -> str:
        """构建分析提示词"""
        prompt = f"""
任务：分析以下信息并提取洞察

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
请分析并返回JSON格式结果：
{
  "insights": ["关键洞察1", "关键洞察2"],
  "contradictions": ["矛盾点1", "矛盾点2"],
  "confidence_score": 0.85,
  "key_findings": ["主要发现1", "主要发现2"]
}
"""
        return prompt
    
    async def _run_llm_analysis(self, prompt: str) -> Dict[str, Any]:
        """
        使用 LLM 执行分析 - 真实实现
        
        支持本地部署的 vllm 服务（OpenAI 兼容 API）
        """
        if not self.llm_config.base_url:
            logger.warning("⚠️ LLM base_url not configured, using fallback")
            return self._fallback_analysis()
        
        logger.debug(f"🤖 Calling LLM for analysis: {self.llm_config.model_name}")
        
        try:
            session = await self._get_llm_session()
            
            # 构建请求（OpenAI 兼容格式）
            request_payload = {
                "model": self.llm_config.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的信息分析助手，擅长从多个来源中提取洞察、识别矛盾和评估信息可信度。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "top_p": self.llm_config.top_p,
                "top_k": self.llm_config.top_k
            }
            
            # 如果要求 JSON 格式
            if self.llm_config.response_format == "json_object":
                request_payload["response_format"] = {"type": "json_object"}
            
            # 设置请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            # 添加 API Key（如果配置了）
            if self.llm_config.api_key:
                headers["Authorization"] = f"Bearer {self.llm_config.api_key}"
            
            # 发送请求
            async with session.post(
                self.llm_config.chat_endpoint,
                json=request_payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ LLM API error: {response.status} - {error_text}")
                    return self._fallback_analysis()
                
                # 解析响应
                response_data = await response.json()
                
                # 提取生成的文本
                choices = response_data.get("choices", [])
                if not choices:
                    logger.warning("⚠️ LLM returned no choices")
                    return self._fallback_analysis()
                
                generated_text = choices[0].get("message", {}).get("content", "")
                
                # 尝试解析 JSON
                try:
                    # 提取 JSON 代码块（如果有）
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', generated_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 直接尝试解析
                        json_str = generated_text.strip()
                    
                    result = json.loads(json_str)
                    
                    # 验证必需字段
                    required_fields = ["insights", "contradictions", "confidence_score", "key_findings"]
                    for field in required_fields:
                        if field not in result:
                            result[field] = []
                            logger.warning(f"⚠️ Missing field in LLM response: {field}")
                    
                    logger.success(f"✅ LLM analysis completed (confidence: {result.get('confidence_score', 0):.2f})")
                    return result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse LLM JSON response: {str(e)}")
                    logger.debug(f"Raw response: {generated_text[:500]}")
                    return self._fallback_analysis()
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ LLM connection error: {str(e)}")
            return self._fallback_analysis()
        except Exception as e:
            logger.error(f"❌ LLM analysis failed: {str(e)}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """分析失败时的回退"""
        return {
            "insights": [],
            "contradictions": [],
            "confidence_score": 0.0,
            "key_findings": [],
            "fallback": True,
            "error": "LLM analysis failed, using fallback"
        }
    
    async def _execute_synthesize_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行综合步骤 - 使用大模型进行多源信息整合
        
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
            previous_steps = step.get("previous_analyses", [])
            
            if not sources:
                logger.warning("⚠️ No sources to synthesize")
                return {
                    "success": False,
                    "type": "synthesize",
                    "error": "No sources provided for synthesis"
                }
            
            # 构建综合提示
            synthesis_prompt = self._build_synthesis_prompt(
                question=question,
                sources=sources,
                previous_analyses=previous_steps
            )
            
            # 使用 LLM 进行综合
            synthesis_result = await self._run_llm_synthesis(synthesis_prompt)
            
            logger.success(f"✅ Synthesis completed: {len(synthesis_result.get('sections', []))} sections")
            
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
    
    def _build_synthesis_prompt(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        previous_analyses: List[Dict[str, Any]]
    ) -> str:
        """构建综合提示词"""
        prompt = f"""
任务：综合多个来源的信息，回答用户问题

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
请综合以上信息，返回JSON格式结果：
{
  "summary": "简洁的总结",
  "key_points": ["关键点1", "关键点2", "关键点3"],
  "supporting_evidence": ["支持证据1", "支持证据2"],
  "contradictions": ["矛盾点1"],
  "sections": [
    {
      "title": "章节标题",
      "content": "章节内容",
      "sources": [1, 2, 3]
    }
  ]
}
"""
        return prompt
    
    async def _run_llm_synthesis(self, prompt: str) -> Dict[str, Any]:
        """
        使用 LLM 执行综合 - 真实实现
        
        支持本地部署的 vllm 服务（OpenAI 兼容 API）
        """
        if not self.llm_config.base_url:
            logger.warning("⚠️ LLM base_url not configured, using fallback")
            return self._fallback_synthesis()
        
        logger.debug(f"🤖 Calling LLM for synthesis: {self.llm_config.model_name}")
        
        try:
            session = await self._get_llm_session()
            
            # 构建请求（OpenAI 兼容格式）
            request_payload = {
                "model": self.llm_config.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的信息整合助手，擅长从多个来源中整合信息、构建连贯的叙述、识别支持或反对证据，并生成平衡的观点。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "top_p": self.llm_config.top_p,
                "top_k": self.llm_config.top_k
            }
            
            # 如果要求 JSON 格式
            if self.llm_config.response_format == "json_object":
                request_payload["response_format"] = {"type": "json_object"}
            
            # 设置请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            # 添加 API Key（如果配置了）
            if self.llm_config.api_key:
                headers["Authorization"] = f"Bearer {self.llm_config.api_key}"
            
            # 发送请求
            async with session.post(
                self.llm_config.chat_endpoint,
                json=request_payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ LLM API error: {response.status} - {error_text}")
                    return self._fallback_synthesis()
                
                # 解析响应
                response_data = await response.json()
                
                # 提取生成的文本
                choices = response_data.get("choices", [])
                if not choices:
                    logger.warning("⚠️ LLM returned no choices")
                    return self._fallback_synthesis()
                
                generated_text = choices[0].get("message", {}).get("content", "")
                
                # 尝试解析 JSON
                try:
                    # 提取 JSON 代码块（如果有）
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', generated_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 直接尝试解析
                        json_str = generated_text.strip()
                    
                    result = json.loads(json_str)
                    
                    # 验证必需字段
                    required_fields = ["summary", "key_points", "supporting_evidence", "contradictions", "sections"]
                    for field in required_fields:
                        if field not in result:
                            result[field] = [] if field != "summary" else ""
                            logger.warning(f"⚠️ Missing field in LLM response: {field}")
                    
                    logger.success(f"✅ LLM synthesis completed (sections: {len(result.get('sections', []))})")
                    return result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse LLM JSON response: {str(e)}")
                    logger.debug(f"Raw response: {generated_text[:500]}")
                    return self._fallback_synthesis()
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ LLM connection error: {str(e)}")
            return self._fallback_synthesis()
        except Exception as e:
            logger.error(f"❌ LLM synthesis failed: {str(e)}")
            return self._fallback_synthesis()
    
    def _fallback_synthesis(self) -> Dict[str, Any]:
        """综合失败时的回退"""
        return {
            "summary": "无法生成综合总结",
            "key_points": [],
            "supporting_evidence": [],
            "contradictions": [],
            "sections": [],
            "fallback": True,
            "error": "LLM synthesis failed, using fallback"
        }
    
    def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重文档来源
        
        Args:
            sources: 原始来源列表
            
        Returns:
            去重后的来源列表
        """
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
        """
        记录步骤到日志
        """
        log_entry = {
            "phase": phase,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_log.append(log_entry)
        logger.debug(f"📊 Logged: {phase}")
    
    def get_execution_trace(self) -> Dict[str, Any]:
        """
        获取完整的执行追踪
        
        Returns:
            执行日志和元数据
        """
        return {
            "query": self.current_query,
            "log": self.execution_log,
            "total_steps": len(self.execution_log),
            "timestamp": datetime.now().isoformat()
        }
