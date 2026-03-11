"""
JQL 验证服务 - 通过 Jira API 验证 JQL 语法和有效性
"""
import json
import requests
from typing import Dict, Any, Optional
from loguru import logger

from config.config import jira_config
from utils.retry import retry_on_rate_limit


class JQLValidator:
    """
    JQL 验证器

    使用 Jira REST API 验证 JQL 查询的语法和有效性
    """

    def __init__(self):
        """初始化 JQL 验证器"""
        self.session = requests.Session()
        logger.info("✅ JQL Validator initialized")

    @retry_on_rate_limit(max_retries=3, delay=1.0)
    async def validate_jql(
        self,
        jql: str,
        access_token: str,
        cloud_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证 JQL 查询

        Args:
            jql: JQL 查询语句
            access_token: OAuth 访问令牌
            cloud_id: Jira Cloud ID（可选，从配置读取）

        Returns:
            验证结果：
            {
                "success": bool,
                "valid": bool,
                "jql": str,
                "error": str,  # 错误信息（如果无效）
                "error_messages": list,  # Jira 返回的错误详情
                "response": dict  # 原始响应
            }
        """
        logger.info(f"🔍 Validating JQL: {jql[:100]}...")

        # 使用配置的 cloud_id 或传入的值
        actual_cloud_id = cloud_id or jira_config.jira_cloud_id

        if not actual_cloud_id:
            logger.warning("⚠️  No JIRA_CLOUD_ID configured, skipping API validation")
            return {
                "success": True,
                "valid": None,  # 未验证
                "jql": jql,
                "warning": "No JIRA_CLOUD_ID configured, API validation skipped"
            }

        # 构建 Jira API URL
        # 使用 Atlassian API 网关格式
        api_url = f"https://api.atlassian.com/ex/jira/{actual_cloud_id}/rest/api/3/search"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        params = {
            "jql": jql,
            "validateQuery": "true",  # 仅验证，不返回结果
            "fields": "key",  # 最小字段集
            "maxResults": 0  # 不返回实际结果
        }

        try:
            response = self.session.get(
                api_url,
                headers=headers,
                params=params,
                timeout=10
            )

            # Jira 返回 200 表示 JQL 有效
            # 返回 400 表示 JQL 语法错误
            if response.status_code == 200:
                logger.success(f"✅ JQL validated successfully")
                return {
                    "success": True,
                    "valid": True,
                    "jql": jql,
                    "response": response.json()
                }

            elif response.status_code == 400:
                # 解析错误信息
                error_data = response.json()
                error_messages = self._extract_error_messages(error_data)

                logger.warning(f"⚠️  JQL validation failed: {error_messages}")
                return {
                    "success": True,
                    "valid": False,
                    "jql": jql,
                    "error": "JQL syntax or semantic error",
                    "error_messages": error_messages,
                    "response": error_data
                }

            else:
                error_msg = f"Jira API returned {response.status_code}"
                logger.error(f"❌ {error_msg}: {response.text}")
                return {
                    "success": False,
                    "valid": None,
                    "jql": jql,
                    "error": error_msg,
                    "response": response.text
                }

        except requests.exceptions.Timeout:
            logger.error("❌ Jira API timeout")
            return {
                "success": False,
                "valid": None,
                "jql": jql,
                "error": "Request timeout"
            }

        except requests.exceptions.ConnectionError:
            logger.error("❌ Jira API connection error")
            return {
                "success": False,
                "valid": None,
                "jql": jql,
                "error": "Connection error"
            }

        except Exception as e:
            logger.error(f"❌ JQL validation error: {str(e)}")
            return {
                "success": False,
                "valid": None,
                "jql": jql,
                "error": str(e)
            }

    def _extract_error_messages(self, error_data: Dict[str, Any]) -> list:
        """
        从 Jira API 错误响应中提取错误消息

        Args:
            error_data: Jira API 返回的错误数据

        Returns:
            错误消息列表
        """
        messages = []

        # 检查 errorMessages 字段
        if "errorMessages" in error_data:
            messages.extend(error_data["errorMessages"])

        # 检查 errors 字段（字段级错误）
        if "errors" in error_data:
            for field, error in error_data["errors"].items():
                messages.append(f"{field}: {error}")

        if not messages:
            messages.append("Unknown validation error")

        return messages

    async def validate_with_suggestions(
        self,
        jql: str,
        access_token: str,
        cloud_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证 JQL 并提供建议（如果无效）

        Args:
            jql: JQL 查询语句
            access_token: OAuth 访问令牌
            cloud_id: Jira Cloud ID

        Returns:
            验证结果（包含建议）
        """
        result = await self.validate_jql(jql, access_token, cloud_id)

        # 如果验证失败，提供建议
        if result.get("success") and not result.get("valid"):
            result["suggestions"] = self._generate_suggestions(
                jql,
                result.get("error_messages", [])
            )

        return result

    def _generate_suggestions(self, jql: str, error_messages: list) -> list:
        """
        根据错误消息生成修复建议

        Args:
            jql: 原始 JQL
            error_messages: 错误消息列表

        Returns:
            建议列表
        """
        suggestions = []

        for error in error_messages:
            error_lower = error.lower()

            if "field" in error_lower and "does not exist" in error_lower:
                suggestions.append("检查字段名是否正确，注意大小写")

            if "operator" in error_lower:
                suggestions.append("检查操作符是否正确，如 =, !=, IN, ~ 等")

            if "value" in error_lower or "quote" in error_lower:
                suggestions.append("字符串值需要用双引号包裹")

            if "parentheses" in error_lower or "bracket" in error_lower:
                suggestions.append("检查括号是否匹配")

            if "expected" in error_lower:
                suggestions.append("检查查询语法，可能缺少操作符或值")

        # 通用建议
        if not suggestions:
            suggestions.append("请检查 JQL 语法，参考 Jira 文档")
            suggestions.append("确保字段名、操作符和值都正确")

        return suggestions

    def close(self):
        """关闭会话"""
        self.session.close()
        logger.debug("✅ JQL Validator closed")


class OAuthHelper:
    """
    OAuth 辅助工具

    帮助处理 Jira OAuth 令牌
    """

    @staticmethod
    def get_user_token_from_header(authorization_header: str) -> Optional[str]:
        """
        从 Authorization header 中提取访问令牌

        Args:
            authorization_header: Authorization header 值

        Returns:
            访问令牌，如果格式无效返回 None
        """
        if not authorization_header:
            return None

        if authorization_header.startswith("Bearer "):
            return authorization_header[7:]

        if authorization_header.startswith("OAuth "):
            return authorization_header[6:]

        return None

    @staticmethod
    def validate_oauth_config() -> tuple[bool, str]:
        """
        验证 OAuth 配置

        Returns:
            (is_valid, error_message)
        """
        errors = []

        if not jira_config.atlassian_domain:
            errors.append("ATLASSIAN_DOMAIN is not configured")

        if not jira_config.jira_client_id:
            errors.append("JIRA_CLIENT_ID is not configured")

        if not jira_config.jira_client_secret:
            errors.append("JIRA_CLIENT_SECRET is not configured")

        if not jira_config.jira_cloud_id:
            errors.append("JIRA_CLOUD_ID is not configured")

        if errors:
            return False, ", ".join(errors)

        return True, ""

    @staticmethod
    def get_oauth_config_for_glean() -> Dict[str, str]:
        """
        获取用于 Glean Admin UI 配置的 OAuth 信息

        Returns:
            OAuth 配置字典
        """
        domain = jira_config.atlassian_domain

        return {
            "clientUrl": f"https://auth.atlassian.com/authorize?audience={domain}.atlassian.net&prompt=consent",
            "authorizationUrl": "https://auth.atlassian.com/oauth/token",
            "scopes": "read:jira-work,read:jira-user,offline_access",
            "description": "Jira JQL Validation OAuth"
        }
