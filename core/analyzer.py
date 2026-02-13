"""
问题分析器 - 理解用户意图和问题复杂度
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

from config.config import ComplexityLevel


class QuestionAnalyzer:
    """
    问题分析器
    
    功能：
    - 识别问题类型
    - 提取关键实体
    - 分析问题复杂度
    - 确定搜索策略
    """
    
    # 问题类型模式
    TYPE_PATTERNS = {
        "policy": [
            r"政策|规定|规则|policy|rule|guideline",
            r"可以|能否|是否|是否可以|怎么样"
        ],
        "process": [
            r"流程|步骤|方法|如何.*做|怎么.*做|process|procedure",
            r"first|then|步骤|step"
        ],
        "comparison": [
            r"对比|比较|区别|差异|vs\.|versus",
            r"和.*的区别|哪个好|better"
        ],
        "factual": [
            r"什么|是谁|多少|何时|哪里|which|who|what|when|where|how many"
        ],
        "troubleshooting": [
            r"问题|错误|失败|无法|problem|error|fail|issue|trouble",
            r"怎么解决|如何修复|解决|修复"
        ],
        "action": [
            r"需要|要做|要求|request|need|require"
        ]
    }
    
    def __init__(self):
        """初始化分析器"""
        logger.info("🧠 Question Analyzer initialized")
    
    def analyze(self, question: str) -> Dict[str, Any]:
        """
        全面分析问题
        
        Args:
            question: 用户问题
            
        Returns:
            分析结果，包含类型、实体、复杂度等
        """
        logger.info(f"📝 Analyzing question: {question[:100]}...")
        
        analysis = {
            "question": question,
            "type": self._identify_type(question),
            "complexity": self._assess_complexity(question),
            "entities": self._extract_entities(question),
            "main_topic": self._extract_main_topic(question),
            "intent": self._identify_intent(question),
            "requires_expertise": self._requires_expertise(question),
            "requires_recent_info": self._requires_recent_info(question),
            "keywords": self._extract_keywords(question)
        }
        
        logger.info(f"✅ Analysis complete:")
        logger.info(f"   Type: {analysis['type']}")
        logger.info(f"   Complexity: {analysis['complexity']}")
        logger.info(f"   Entities: {analysis['entities']}")
        logger.info(f"   Main Topic: {analysis['main_topic']}")
        
        return analysis
    
    def _identify_type(self, question: str) -> str:
        """
        识别问题类型
        """
        question_lower = question.lower()
        
        # 检查每种类型模式
        for q_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return q_type
        
        return "general"
    
    def _assess_complexity(self, question: str) -> ComplexityLevel:
        """
        评估问题复杂度
        """
        # 复杂度指标
        indicators = {
            "length": len(question.split()),
            "questions": question.count("?") + question.count("？"),
            "conjunctions": len(re.findall(r"\b(and|or|but|however|although|同时|另外)\b", question.lower())),
            "subquestions": len(re.findall(r"\b(what|how|why|when|where|which)\b", question.lower())),
            "entities": len(self._extract_entities(question)),
            "modifiers": len(re.findall(r"\b(current|new|old|recent|past|future|previous)\b", question.lower()))
        }
        
        # 计算复杂度分数
        complexity_score = (
            indicators["length"] * 0.1 +
            indicators["questions"] * 2 +
            indicators["conjunctions"] * 1.5 +
            indicators["subquestions"] * 1 +
            indicators["entities"] * 0.5 +
            indicators["modifiers"] * 0.5
        )
        
        # 根据分数确定复杂度级别
        if complexity_score < 3:
            return ComplexityLevel.SIMPLE
        elif complexity_score < 6:
            return ComplexityLevel.MODERATE
        elif complexity_score < 10:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def _extract_entities(self, question: str) -> List[str]:
        """
        提取实体 - 改进版，不限制数量
        
        策略：
        - 提取有意义的多字词（中文≥2字，英文≥3字母）
        - 过滤停用词
        - 按重要性排序（名词优先）
        - 支持专业术语识别
        """
        # 扩展停用词列表
        stop_words = {
            # 中文停用词
            "的", "是", "在", "和", "或", "但", "了", "吗", "呢", "啊", "吧",
            "这个", "那个", "什么", "怎么", "如何", "哪个", "哪些", "关于",
            "对于", "由于", "因为", "所以", "如果", "虽然", "但是", "然后",
            "接着", "最后", "首先", "其次", "再者", "还有", "另外", "此外",
            # 英文停用词
            "the", "is", "in", "and", "or", "but", "of", "to", "a", "an",
            "what", "how", "why", "when", "where", "which", "that", "this",
            "with", "for", "from", "about", "into", "through", "during"
        }
        
        # 专业术语模式（可根据领域扩展）
        technical_patterns = [
            r"[A-Z]{2,}",  # 缩写词如API, SSO
            r"[a-z]+(?:-[a-z]+)+",  # 连字符词如multi-step
            r"[A-Z][a-z]+(?:[A-Z][a-z]+)+",  # 驼峰词如KnowledgeBase
        ]
        
        # 分词（支持中文和英文）
        words = re.findall(r"[\w\u4e00-\u9fa5-]+", question)
        
        # 过滤和评分实体
        entities_with_score = []
        for word in words:
            word_lower = word.lower()
            
            # 跳过停用词和单字
            if word_lower in stop_words:
                continue
            
            # 跳过过短的词
            if len(word) < 2:
                continue
            
            # 计算重要性分数
            score = 0
            
            # 长度加分
            score += min(len(word) / 3, 3)
            
            # 专业术语加分
            for pattern in technical_patterns:
                if re.fullmatch(pattern, word):
                    score += 3
                    break
            
            # 首字母大写加分（英文专有名词）
            if word[0].isupper() and not word.isupper():
                score += 1
            
            # 包含数字的术语加分（如版本号、年份）
            if re.search(r"\d", word):
                score += 0.5
            
            # 中文多字词加分
            if re.search(r"[\u4e00-\u9fa5]{3,}", word):
                score += 2
            
            entities_with_score.append((word, score))
        
        # 按分数排序
        entities_with_score.sort(key=lambda x: x[1], reverse=True)
        
        # 提取所有实体（不再限制数量）
        entities = [word for word, score in entities_with_score]
        
        # 返回结果（包含所有识别的实体）
        return entities
    
    def _extract_main_topic(self, question: str) -> str:
        """
        提取主要话题
        """
        # 移除疑问词和修饰词
        question_clean = re.sub(
            r"\b(what|how|why|when|where|which|the|is|are|can|could|would|should|"
            r"could|would|should|do|does|did|will|may|might|"
            r"current|new|old|recent|past|future|previous|"
            r"any|some|all|many|much|more|less|"
            r"please|help|need|want|know|understand|tell|explain|describe|"
            r"关于|对于|regarding|about)\b",
            "",
            question,
            flags=re.IGNORECASE
        )
        
        # 提取名词性短语
        words = re.findall(r"[\w\u4e00-\u9fa5]+", question_clean)
        
        if words:
            # 返回前2个词作为主要话题
            return " ".join(words[:2])
        
        return question[:20]  # 如果无法提取，返回问题的前20个字符
    
    def _identify_intent(self, question: str) -> str:
        """
        识别用户意图
        """
        question_lower = question.lower()
        
        # 意图模式
        intents = {
            "search": ["查找", "搜索", "找", "search", "find", "look for"],
            "explain": ["解释", "说明", "什么是", "explain", "what is", "describe"],
            "compare": ["对比", "比较", "区别", "compare", "difference", "vs"],
            "procedure": ["如何", "怎么", "步骤", "how to", "process", "steps"],
            "troubleshoot": ["解决", "修复", "问题", "solve", "fix", "issue", "problem"],
            "update": ["最新", "当前", "更新", "latest", "current", "update"],
            "policy": ["政策", "规定", "允许", "禁止", "policy", "rule", "allow", "prohibit"],
            "recommendation": ["推荐", "建议", "最好", "recommend", "suggest", "best"],
            "warning": ["注意", "风险", "警告", "note", "risk", "warning", "caution"]
        }
        
        for intent, patterns in intents.items():
            for pattern in patterns:
                if pattern in question_lower:
                    return intent
        
        return "general"
    
    def _requires_expertise(self, question: str) -> bool:
        """
        判断是否需要专业知识
        """
        expertise_indicators = [
            r"\b(expert|specialist|专业|专家|approval|审批|compliance|合规)\b",
            r"\b(technical|技术|legal|法律|financial|财务|security|安全)\b",
            r"\b(review|audit|审查|审计)\b",
            r"\b(configuration|配置|deployment|部署|implementation|实施)\b"
        ]
        
        question_lower = question.lower()
        for pattern in expertise_indicators:
            if re.search(pattern, question_lower):
                return True
        
        return False
    
    def _requires_recent_info(self, question: str) -> bool:
        """
        判断是否需要最新信息
        """
        recent_indicators = [
            r"\b(current|new|latest|recent|现在|最新|当前|最近|this year|今年|本月)\b",
            r"\b(2024|2025|2026)\b"  # 年份
        ]
        
        question_lower = question.lower()
        for pattern in recent_indicators:
            if re.search(pattern, question_lower):
                return True
        
        return False
    
    def _extract_keywords(self, question: str) -> List[str]:
        """
        提取关键词
        """
        # 移除停用词
        stop_words = {
            "的", "是", "在", "和", "或", "但", "了", "吗", "呢", "啊", "吧",
            "the", "is", "in", "and", "or", "but", "of", "to", "a", "an",
            "what", "how", "why", "when", "where", "which", "that", "this"
        }
        
        # 提取有意义词
        words = re.findall(r"[\w\u4e00-\u9fa5]+", question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # 去重并返回
        return list(set(keywords))