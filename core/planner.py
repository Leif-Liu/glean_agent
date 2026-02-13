"""
问题规划器 - 将复杂问题分解为可执行的子任务
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from config.config import (
    agent_config, ComplexityLevel, SearchMode
)


class QuestionPlanner:
    """
    问题规划器
    
    功能：
    - 分析问题复杂度
    - 分解复杂问题为子任务
    - 生成执行计划
    - 优化搜索策略
    - 识别任务依赖关系
    """
    
    def __init__(self):
        """初始化规划器"""
        self.complexity_thresholds = agent_config.complexity_thresholds
        
        logger.info("🎯 Question Planner initialized")
    
    def decompose(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分解问题为可执行的子任务
        
        Args:
            question: 原始问题
            analysis: 问题分析结果
            
        Returns:
            执行计划，包含步骤、策略、依赖等
        """
        logger.info(f"🎯 Decomposing question: {question[:50]}...")
        
        complexity = analysis["complexity"]
        question_type = analysis["type"]
        entities = analysis["entities"]
        
        # 根据复杂度生成计划
        if complexity == ComplexityLevel.SIMPLE:
            plan = self._plan_simple(question, analysis)
        elif complexity == ComplexityLevel.MODERATE:
            plan = self._plan_moderate(question, analysis)
        elif complexity == ComplexityLevel.COMPLEX:
            plan = self._plan_complex(question, analysis)
        else:  # VERY_COMPLEX
            plan = self._plan_very_complex(question, analysis)
        
        # 优化计划
        plan = self._optimize_plan(plan, analysis)
        
        logger.info(f"✅ Plan generated with {len(plan['steps'])} steps")
        logger.info(f"   Estimated time: {plan.get('estimated_time', 'unknown')}")
        
        return plan
    
    def _plan_simple(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        简单问题计划（单轮搜索）
        
        策略：
        - 直接搜索
        - 检索文档
        - 总结答案
        """
        logger.info("📝 Planning: Simple question (1 search)")
        
        return {
            "question": question,
            "complexity": "simple",
            "strategy": "direct_search",
            "estimated_time": "30-60s",
            "steps": [
                {
                    "step_id": "search_1",
                    "description": f"Search for: {question}",
                    "type": "search",
                    "query": question,
                    "mode": SearchMode.BASIC,
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "step_id": "retrieve_1",
                    "description": "Retrieve document contents",
                    "type": "retrieve",
                    "priority": 2,
                    "dependencies": ["search_1"]
                },
                {
                    "step_id": "synthesize_1",
                    "description": "Generate final answer",
                    "type": "synthesize",
                    "question": question,
                    "entities": analysis.get("entities", []),
                    "priority": 3,
                    "dependencies": ["retrieve_1"]
                }
            ]
        }
    
    def _plan_moderate(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        中等复杂度问题计划（2-3轮搜索）
        
        策略：
        - 主搜索
        - 基于实体的补充搜索
        - 检索和整合
        """
        logger.info("📝 Planning: Moderate question (2-3 searches)")
        
        entities = analysis.get("entities", [])
        main_entities = entities[:3]  # 最多3个主要实体
        
        steps = [
            {
                "step_id": "search_main",
                "description": f"Main search for: {question}",
                "type": "search",
                "query": question,
                "mode": SearchMode.HYBRID,
                "priority": 1,
                "dependencies": []
            }
        ]
        
        # 为每个主要实体添加搜索
        for idx, entity in enumerate(main_entities, 1):
            steps.append({
                "step_id": f"search_entity_{idx}",
                "description": f"Search for entity: {entity}",
                "type": "search",
                "query": f'"{entity}"',  # 精确匹配
                "mode": SearchMode.BASIC,
                "priority": 2,
                "dependencies": []
            })
        
        steps.extend([
            {
                "step_id": "analyze_results",
                "description": "Analyze and cross-reference results",
                "type": "analyze",
                "entities": entities,
                "priority": 3,
                "dependencies": [s["step_id"] for s in steps if s["type"] == "search"]
            },
            {
                "step_id": "retrieve_docs",
                "description": "Retrieve full document contents",
                "type": "retrieve",
                "priority": 4,
                "dependencies": [s["step_id"] for s in steps if s["type"] == "search"]
            },
            {
                "step_id": "synthesize_final",
                "description": "Generate comprehensive answer",
                "type": "synthesize",
                "question": question,
                "entities": entities,
                "priority": 5,
                "dependencies": ["analyze_results", "retrieve_docs"]
            }
        ])
        
        return {
            "question": question,
            "complexity": "moderate",
            "strategy": "multi_search",
            "estimated_time": "60-120s",
            "steps": steps
        }
    
    def _plan_complex(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        复杂问题计划（3-5轮搜索）
        
        策略：
        - 语义搜索
        - 多角度搜索
        - 深度挖掘
        - 交叉验证
        """
        logger.info("📝 Planning: Complex question (3-5 searches)")
        
        question_type = analysis["type"]
        entities = analysis.get("entities", [])
        
        steps = [
            {
                "step_id": "search_semantic",
                "description": "Semantic search for main query",
                "type": "search",
                "query": question,
                "mode": SearchMode.SEMANTIC,
                "priority": 1,
                "dependencies": []
            },
            {
                "step_id": "search_contextual",
                "description": "Contextual search with expanded query",
                "type": "search",
                "query": f"{question} {question_type}",
                "mode": SearchMode.HYBRID,
                "priority": 2,
                "dependencies": []
            }
        ]
        
        # 基于问题类型添加专门搜索
        if question_type == "comparison":
            steps.append({
                "step_id": "search_comparison",
                "description": "Search for comparison data",
                "type": "search",
                "query": f"comparison {question}",
                "mode": SearchMode.BASIC,
                "priority": 3,
                "dependencies": []
            })
        elif question_type == "process":
            steps.append({
                "step_id": "search_procedure",
                "description": "Search for procedures and steps",
                "type": "search",
                "query": f"procedure process {question}",
                "mode": SearchMode.BASIC,
                "priority": 3,
                "dependencies": []
            })
        
        # 为关键实体添加深度搜索
        if entities:
            steps.append({
                "step_id": "search_deep",
                "description": f"Deep search for key entities",
                "type": "search",
                "query": " AND ".join(entities[:4]),  # 最多4个实体
                "mode": SearchMode.DEEP,
                "priority": 4,
                "dependencies": []
            })
        
        steps.extend([
            {
                "step_id": "analyze_cross_reference",
                "description": "Cross-reference and validate results",
                "type": "analyze",
                "analysis_type": "cross_reference",
                "entities": entities,
                "priority": 5,
                "dependencies": [s["step_id"] for s in steps if s["type"] == "search"]
            },
            {
                "step_id": "retrieve_full_docs",
                "description": "Retrieve and analyze full documents",
                "type": "retrieve",
                "priority": 6,
                "dependencies": ["analyze_cross_reference"]
            },
            {
                "step_id": "synthesize_comprehensive",
                "description": "Generate comprehensive answer with evidence",
                "type": "synthesize",
                "question": question,
                "entities": entities,
                "priority": 7,
                "dependencies": ["analyze_cross_reference", "retrieve_full_docs"]
            }
        ])
        
        return {
            "question": question,
            "complexity": "complex",
            "strategy": "multi_angle_deep",
            "estimated_time": "120-180s",
            "steps": steps
        }
    
    def _plan_very_complex(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        非常复杂问题计划（5-7轮搜索）
        
        策略：
        - 多阶段搜索
        - 迭代优化
        - 专家知识
        - 多源验证
        """
        logger.info("📝 Planning: Very complex question (5-7 searches)")
        
        question_type = analysis["type"]
        entities = analysis.get("entities", [])
        requires_expertise = analysis.get("requires_expertise", False)
        requires_recent = analysis.get("requires_recent_info", False)
        
        # 第一阶段：广泛搜索
        stage1_steps = [
            {
                "step_id": "search_broad_1",
                "description": "Broad semantic search",
                "type": "search",
                "query": question,
                "mode": SearchMode.SEMANTIC,
                "priority": 1,
                "dependencies": []
            },
            {
                "step_id": "search_broad_2",
                "description": "Contextual search",
                "type": "search",
                "query": f"{question} {question_type} documentation",
                "mode": SearchMode.HYBRID,
                "priority": 1,
                "dependencies": []
            }
        ]
        
        # 第二阶段：深度搜索
        stage2_steps = []
        
        if requires_expertise:
            stage2_steps.append({
                "step_id": "search_expert",
                "description": "Search for expert documentation",
                "type": "search",
                "query": f"expert official {question}",
                "mode": SearchMode.BASIC,
                "priority": 2,
                "dependencies": ["search_broad_1"]
            })
        
        if requires_recent:
            stage2_steps.append({
                "step_id": "search_recent",
                "description": "Search for recent updates",
                "type": "search",
                "query": f"latest recent {question}",
                "mode": SearchMode.BASIC,
                "filters": {
                    "timeRange": "past_month"
                },
                "priority": 2,
                "dependencies": ["search_broad_1"]
            })
        
        # 基于实体的深度搜索
        if entities:
            stage2_steps.append({
                "step_id": "search_entities_deep",
                "description": "Deep search for all entities",
                "type": "search",
                "query": " OR ".join(entities[:5]),
                "mode": SearchMode.DEEP,
                "priority": 2,
                "dependencies": []
            })
        
        # 第三阶段：分析和综合
        stage3_steps = [
            {
                "step_id": "analyze_phase1",
                "description": "Analyze initial results",
                "type": "analyze",
                "analysis_type": "initial",
                "entities": entities,
                "priority": 3,
                "dependencies": [s["step_id"] for s in stage1_steps]
            },
            {
                "step_id": "analyze_phase2",
                "description": "Analyze deep results",
                "type": "analyze",
                "analysis_type": "deep",
                "entities": entities,
                "priority": 4,
                "dependencies": [s["step_id"] for s in stage2_steps]
            },
            {
                "step_id": "synthesize_intermediate",
                "description": "Synthesize and identify gaps",
                "type": "synthesize",
                "question": question,
                "entities": entities,
                "priority": 5,
                "dependencies": ["analyze_phase2"]
            }
        ]
        
        # 第四阶段：迭代优化
        stage4_steps = [
            {
                "step_id": "retrieve_all_docs",
                "description": "Retrieve all relevant documents",
                "type": "retrieve",
                "priority": 6,
                "dependencies": ["synthesize_intermediate"]
            },
            {
                "step_id": "synthesize_final",
                "description": "Generate final comprehensive answer",
                "type": "synthesize",
                "question": question,
                "entities": entities,
                "priority": 7,
                "dependencies": ["retrieve_all_docs"]
            }
        ]
        
        all_steps = stage1_steps + stage2_steps + stage3_steps + stage4_steps
        
        return {
            "question": question,
            "complexity": "very_complex",
            "strategy": "iterative_multi_stage",
            "estimated_time": "180-300s",
            "steps": all_steps
        }
    
    def _optimize_plan(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        优化执行计划
        
        策略：
        - 合并相似步骤
        - 优化搜索查询
        - 调整优先级
        - 添加过滤器
        """
        steps = plan["steps"]
        
        # 为搜索步骤添加时间过滤器（如果需要最新信息）
        if analysis.get("requires_recent_info"):
            for step in steps:
                if step["type"] == "search":
                    if "filters" not in step:
                        step["filters"] = {}
                    step["filters"]["timeRange"] = "past_month"
        
        # 优化查询
        for step in steps:
            if step["type"] == "search" and "query" in step:
                step["query"] = self._optimize_query(step["query"], analysis)
        
        return plan
    
    def _optimize_query(
        self,
        query: str,
        analysis: Dict[str, Any]
    ) -> str:
        """
        优化搜索查询
        
        策略：
        - 添加关键词
        - 移除冗余词
        - 优化词序
        """
        # 简化实现：返回原始查询
        # 实际可以根据问题类型和实体进行优化
        return query
