"""
JQL 转换服务 - 使用 Glean Chat API 将自然语言转换为 JQL
"""
import json
import re
from typing import Dict, Any, Optional
from loguru import logger

from modules.glean_chat_wrapper import GleanChatWrapper
from prompts.jql_conversion import get_conversion_prompt, get_fewshot_prompt


class JQLConverter:
    """
    JQL 转换器

    使用 Glean Chat API 将自然语言查询转换为有效的 JQL 语句
    """

    def __init__(self):
        """初始化 JQL 转换器"""
        self.glean_chat = GleanChatWrapper()
        logger.info("🔄 JQL Converter initialized")

    async def convert_to_jql(
        self,
        natural_query: str,
        project_context: Optional[str] = None,
        use_fewshot: bool = True
    ) -> Dict[str, Any]:
        """
        将自然语言查询转换为 JQL

        Args:
            natural_query: 用户的自然语言查询
            project_context: 项目上下文信息（可选）
            use_fewshot: 是否使用 few-shot 示例

        Returns:
            转换结果：
            {
                "success": bool,
                "jql": str,  # 生成的 JQL
                "explanation": str,  # 查询说明
                "fields_used": list,  # 使用的字段
                "raw_response": Any,  # 原始响应
                "error": str  # 错误信息（失败时）
            }
        """
        logger.info(f"🔄 Converting to JQL: {natural_query[:100]}...")

        try:
            # 构建提示词
            if use_fewshot:
                prompt = get_fewshot_prompt(natural_query)
            else:
                prompt = get_conversion_prompt(natural_query, project_context or "")

            # 调用 Glean Chat API
            response = await self.glean_chat.ask_async(
                question=prompt,
                timeout_millis=30000
            )

            if not response.get("success"):
                error = response.get("error", "Unknown error from Glean Chat")
                logger.error(f"❌ Glean Chat API failed: {error}")
                return {
                    "success": False,
                    "error": f"Glean Chat API error: {error}"
                }

            # 提取 JQL 结果
            result = self._extract_jql_from_response(response.get("answer", ""))

            if result["success"]:
                logger.success(f"✅ JQL generated: {result['jql']}")
            else:
                logger.warning(f"⚠️  JQL extraction failed: {result.get('error', 'Unknown error')}")

            return result

        except Exception as e:
            logger.error(f"❌ JQL conversion error: {str(e)}")
            return {
                "success": False,
                "error": f"JQL conversion failed: {str(e)}"
            }

    def _extract_jql_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        从 Glean Chat 响应中提取 JQL

        Args:
            response_text: Glean Chat API 返回的响应文本

        Returns:
            提取结果：
            {
                "success": bool,
                "jql": str,
                "explanation": str,
                "fields_used": list,
                "error": str
            }
        """
        # 尝试解析 JSON 格式的响应
        json_match = self._extract_json(response_text)

        if json_match:
            # 验证必需字段
            if "jql" not in json_match:
                return {
                    "success": False,
                    "error": "Response missing required 'jql' field"
                }

            # 验证 JQL 格式
            jql = json_match.get("jql", "").strip()
            if not self._validate_jql_syntax(jql):
                return {
                    "success": False,
                    "error": f"Generated JQL has invalid syntax: {jql}"
                }

            return {
                "success": True,
                "jql": jql,
                "explanation": json_match.get("explanation", ""),
                "fields_used": json_match.get("fields_used", []),
                "raw_response": json_match
            }

        # 如果不是 JSON，尝试从文本中提取
        text_match = self._extract_jql_from_text(response_text)
        if text_match:
            return {
                "success": True,
                "jql": text_match,
                "explanation": "Extracted from text response",
                "fields_used": []
            }

        return {
            "success": False,
            "error": "Could not extract valid JQL from response"
        }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取 JSON 对象

        Args:
            text: 包含 JSON 的文本

        Returns:
            解析后的 JSON 对象，如果失败返回 None
        """
        # 尝试匹配 JSON 代码块
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, text, re.DOTALL)

        if match:
            json_str = match.group(1)
        else:
            # 尝试匹配整个 JSON 对象
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            match = re.search(json_pattern, text, re.DOTALL)

            if not match:
                return None

            json_str = match.group(0)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def _extract_jql_from_text(self, text: str) -> Optional[str]:
        """
        从纯文本中提取 JQL 语句

        Args:
            text: 文本内容

        Returns:
            提取的 JQL 语句，如果没有则返回 None
        """
        # 查找可能的 JQL 模式
        jql_patterns = [
            r'JQL:\s*([^\n]+)',  # JQL: xxx
            r'jql\s*=\s*"([^"]+)"',  # jql = "xxx"
            r'query:\s*([^\n]+)',  # query: xxx
        ]

        for pattern in jql_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                jql = match.group(1).strip()
                if self._validate_jql_syntax(jql):
                    return jql

        return None

    def _validate_jql_syntax(self, jql: str) -> bool:
        """
        基本验证 JQL 语法

        注意：这只是语法检查，真正的验证需要通过 Jira API

        Args:
            jql: JQL 语句

        Returns:
            语法是否基本有效
        """
        if not jql or not jql.strip():
            return False

        jql = jql.strip()

        # 检查是否有基本的操作符
        operators = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', '~', '!~', 'IS', 'WAS']
        has_operator = any(op in jql for op in operators)

        if not has_operator:
            return False

        # 检查括号是否匹配
        if jql.count('(') != jql.count(')'):
            return False

        # 检查字符串引号是否匹配
        if jql.count('"') % 2 != 0:
            return False

        # 检查是否有逻辑连接词（多个条件时）
        if ' AND ' in jql or ' OR ' in jql or ' NOT ' in jql:
            return True

        # 单个条件也可以是有效的
        return True

    async def convert_with_retry(
        self,
        natural_query: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带重试的 JQL 转换

        Args:
            natural_query: 自然语言查询
            max_retries: 最大重试次数
            **kwargs: 其他参数传递给 convert_to_jql

        Returns:
            转换结果
        """
        for attempt in range(max_retries):
            result = await self.convert_to_jql(natural_query, **kwargs)

            if result["success"]:
                return result

            # 如果失败，记录日志并重试
            if attempt < max_retries - 1:
                logger.warning(f"⚠️  JQL conversion attempt {attempt + 1} failed, retrying...")
                continue

        # 所有重试都失败
        logger.error(f"❌ JQL conversion failed after {max_retries} attempts")
        return result

    def close(self):
        """关闭连接"""
        self.glean_chat.close()
        logger.debug("🔄 JQL Converter closed")
