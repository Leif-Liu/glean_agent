"""
Glean Action Server - FastAPI Web Server

提供将自然语言转换为 JQL 的 HTTP API 端点
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger
import uvicorn

from config.config import action_server_config, jira_config
from actions.jql_converter import JQLConverter
from actions.jql_validator import JQLValidator, OAuthHelper


# Request/Response Models
class JQLConversionRequest(BaseModel):
    """JQL 转换请求"""
    query: str = Field(..., description="自然语言查询描述", min_length=1)
    project_context: Optional[str] = Field(None, description="项目上下文信息（可选）")
    use_fewshot: bool = Field(True, description="是否使用 Few-Shot 示例")
    validate: bool = Field(True, description="是否通过 Jira API 验证")


class JQLConversionResponse(BaseModel):
    """JQL 转换响应"""
    success: bool = Field(..., description="转换是否成功")
    jql: Optional[str] = Field(None, description="生成的 JQL 查询")
    explanation: Optional[str] = Field(None, description="查询说明")
    fields_used: list = Field(default_factory=list, description="使用的字段列表")
    validated: Optional[bool] = Field(None, description="是否通过 Jira API 验证")
    validation_error: Optional[str] = Field(None, description="验证错误信息（如果验证失败）")
    validation_suggestions: list = Field(default_factory=list, description="验证修复建议")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    oauth_configured: bool


class ConfigResponse(BaseModel):
    """配置信息响应"""
    oauth_config: Dict[str, str]
    endpoints: Dict[str, str]


# 全局实例
converter: Optional[JQLConverter] = None
validator: Optional[JQLValidator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global converter, validator

    # 启动时初始化
    logger.info("=" * 60)
    logger.info("🚀 Starting Glean Action Server")
    logger.info("=" * 60)

    converter = JQLConverter()
    validator = JQLValidator()

    # 检查 OAuth 配置
    oauth_valid, oauth_error = OAuthHelper.validate_oauth_config()
    if not oauth_valid:
        logger.warning(f"⚠️  OAuth not configured: {oauth_error}")
        logger.warning("⚠️  JQL validation will be skipped")
    else:
        logger.success("✅ OAuth configuration is valid")

    yield

    # 关闭时清理
    logger.info("🛑 Shutting down Glean Action Server")
    if converter:
        converter.close()
    if validator:
        validator.close()


# 创建 FastAPI 应用
app = FastAPI(
    title=action_server_config.api_title,
    version=action_server_config.api_version,
    description="Glean Action Server for Natural Language to JQL Conversion",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    oauth_valid, _ = OAuthHelper.validate_oauth_config()

    return {
        "status": "healthy",
        "version": action_server_config.api_version,
        "oauth_configured": oauth_valid
    }


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取配置信息（用于 Glean Admin UI 配置）"""
    oauth_config = OAuthHelper.get_oauth_config_for_glean()

    return {
        "oauth_config": oauth_config,
        "endpoints": {
            "convert": "/convert_to_jql",
            "health": "/health",
            "openapi": "/openapi.json"
        }
    }


@app.post("/convert_to_jql", response_model=JQLConversionResponse)
async def convert_to_jql(
    request: JQLConversionRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    glean_user_email: Optional[str] = Header(None, alias="Glean-User-Email")
):
    """
    将自然语言转换为 JQL 并验证

    该端点接收自然语言查询，使用 Glean Chat API 转换为 JQL，
    可选地通过 Jira API 验证生成的 JQL。

    **请求头：**
    - `Authorization`: OAuth Bearer 令牌（如果 validate=true）
    - `Glean-User-Email`: Glean 用户邮箱（可选）

    **请求体：**
    ```json
    {
      "query": "查找所有高优先级的 Bug",
      "project_context": "项目 KEY1 的工单",
      "use_fewshot": true,
      "validate": true
    }
    ```

    **响应：**
    ```json
    {
      "success": true,
      "jql": "priority = \"Highest\" AND issuetype = \"Bug\"",
      "explanation": "查询优先级为最高且问题类型为Bug的工单",
      "fields_used": ["priority", "issuetype"],
      "validated": true,
      "validation_error": null,
      "validation_suggestions": [],
      "error": null
    }
    ```
    """
    logger.info(f"📥 Received request: {request.query[:50]}...")

    # 检查 converter 是否初始化
    if not converter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Converter not initialized"
        )

    # 转换为 JQL
    conversion_result = await converter.convert_to_jql(
        natural_query=request.query,
        project_context=request.project_context,
        use_fewshot=request.use_fewshot
    )

    if not conversion_result["success"]:
        return JQLConversionResponse(
            success=False,
            error=conversion_result.get("error", "JQL conversion failed")
        )

    jql = conversion_result["jql"]

    # 如果需要验证
    validated = None
    validation_error = None
    validation_suggestions = []

    if request.validate:
        # 检查 OAuth 令牌
        access_token = OAuthHelper.get_user_token_from_header(authorization)
        if not access_token:
            logger.warning("⚠️  No Authorization header, skipping validation")
            validated = None
        else:
            # 验证 JQL
            validation_result = await validator.validate_with_suggestions(
                jql=jql,
                access_token=access_token
            )

            validated = validation_result.get("valid")
            validation_error = validation_result.get("error")

            if validated is False:
                validation_error = validation_result.get("error_messages", ["Unknown error"])[0]
                validation_suggestions = validation_result.get("suggestions", [])
                logger.warning(f"⚠️  JQL validation failed: {validation_error}")

    # 构建响应
    response = JQLConversionResponse(
        success=True,
        jql=jql,
        explanation=conversion_result.get("explanation", ""),
        fields_used=conversion_result.get("fields_used", []),
        validated=validated,
        validation_error=validation_error,
        validation_suggestions=validation_suggestions
    )

    logger.success(f"✅ Request completed: {jql[:50]}...")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if action_server_config.log_level == "DEBUG" else None
        }
    )


def run_server():
    """
    启动 Action Server

    Usage:
        python main.py action-server
    """
    logger.info("=" * 60)
    logger.info("🌐 Glean JQL Action Server")
    logger.info("=" * 60)
    logger.info(f"Host: {action_server_config.host}")
    logger.info(f"Port: {action_server_config.port}")
    logger.info(f"Version: {action_server_config.api_version}")
    logger.info("=" * 60)
    logger.info("\n📋 Available endpoints:")
    logger.info("  POST /convert_to_jql  - Convert NL to JQL")
    logger.info("  GET  /health           - Health check")
    logger.info("  GET  /config           - Get configuration")
    logger.info("  GET  /docs             - API documentation")
    logger.info("=" * 60)

    # 检查 OAuth 配置
    oauth_valid, oauth_error = OAuthHelper.validate_oauth_config()
    if not oauth_valid:
        logger.warning("\n⚠️  WARNING: OAuth is not properly configured!")
        logger.warning(f"   {oauth_error}")
        logger.warning("   JQL validation will be skipped.")
        logger.warning("   Please set the following environment variables:")
        logger.warning("   - ATLASSIAN_DOMAIN")
        logger.warning("   - JIRA_CLIENT_ID")
        logger.warning("   - JIRA_CLIENT_SECRET")
        logger.warning("   - JIRA_CLOUD_ID")
        logger.warning("")

    uvicorn.run(
        app,
        host=action_server_config.host,
        port=action_server_config.port,
        log_level=action_server_config.log_level.lower()
    )


if __name__ == "__main__":
    run_server()
