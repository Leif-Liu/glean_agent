"""
数据源管理模块 - 管理自定义数据源和索引任务
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from config.config import glean_config
from glean.api_client import Glean, models


class DataSourceManager:
    """
    数据源管理器
    
    功能：
    - 创建和管理自定义数据源
    - 批量索引文档
    - 监控索引状态
    - 处理索引任务队列
    """
    
    def __init__(self):
        """初始化数据源管理器"""
        self.indexing_client = None
        self.indexing_tasks: Dict[str, Dict[str, Any]] = {}
        
        logger.info("📂 Data Source Manager initialized")
    
    def _get_indexing_client(self):
        """获取 Indexing API 客户端"""
        if self.indexing_client is None:
            try:
                from glean.api_client import Glean
                self.indexing_client = Glean(
                    instance=glean_config.instance,
                    api_token=glean_config.indexing_api_token
                )
                logger.info("🔌 Indexing API client initialized")
            except ImportError:
                logger.warning("⚠️ Glean client not available for indexing")
            except Exception as e:
                logger.error(f"❌ Failed to initialize indexing client: {str(e)}")
        
        return self.indexing_client
    
    def create_datasource(
        self,
        name: str,
        display_name: Optional[str] = None,
        category: str = "PUBLISHED_CONTENT",
        url_regex: Optional[str] = None,
        is_user_referenced_by_email: bool = True
    ) -> Dict[str, Any]:
        """
        创建数据源 - 使用正确的 SDK 方法

        Args:
            name: 数据源唯一标识
            display_name: 显示名称
            category: 数据源类别
            url_regex: URL 匹配正则
            is_user_referenced_by_email: 是否通过邮箱引用用户

        Returns:
            数据源创建结果
        """
        logger.info(f"📦 Creating datasource: {name}")

        client = self._get_indexing_client()
        if not client:
            return {
                "success": False,
                "error": "Indexing client not available"
            }

        # 使用 SDK 的 DatasourceConfig 模型
        datasource_config = models.DatasourceConfig(
            name=name,
            display_name=display_name or name.replace("-", " ").title(),
            datasource_category=category,
            is_user_referenced_by_email=is_user_referenced_by_email,
            url_regex=url_regex
        )

        try:
            # 调用正确的 Indexing API: client.indexing.datasources.add()
            response = client.indexing.datasources.add(
                datasource=datasource_config
            )

            logger.success(f"✅ Datasource '{name}' created successfully")
            return {
                "success": True,
                "datasource_id": name,
                "response": response
            }

        except Exception as e:
            logger.error(f"❌ Failed to create datasource: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def index_single_document(
        self,
        datasource: str,
        doc_id: str,
        title: str,
        body: str,
        view_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        mime_type: str = "text/html",
        updated_at: Optional[str] = None,
        container_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        索引单个文档 - 使用正确的 SDK 方法

        Args:
            datasource: 数据源名称
            doc_id: 文档唯一 ID
            title: 文档标题
            body: 文档内容
            view_url: 查看 URL
            metadata: 元数据
            mime_type: MIME 类型
            updated_at: 更新时间
            container_id: 容器 ID（必需）

        Returns:
            索引结果
        """
        logger.info(f"📄 Indexing document: {doc_id}")

        client = self._get_indexing_client()
        if not client:
            return {
                "success": False,
                "error": "Indexing client not available"
            }

        # 使用 SDK 的 Document 和 DocumentBody 模型
        try:
            document_body = models.DocumentBody(
                mime_type=mime_type,
                text_content=body
            )

            # 如果有 HTML，也可以使用 html_content
            if mime_type.startswith("text/html"):
                document_body = models.DocumentBody(
                    mime_type=mime_type,
                    html_content=body
                )

            # 构建文档
            document = models.Document(
                id=doc_id,
                title=title,
                body=document_body,
                view_url=view_url,
                datasource=datasource,
                container_id=container_id or datasource,  # 必需字段
                metadata=metadata,
                updated_at=updated_at
            )

            # 调用正确的 Indexing API: client.indexing.documents.add_or_update()
            response = client.indexing.documents.add_or_update(
                document=document
            )

            logger.success(f"✅ Document '{doc_id}' indexed successfully")
            return {
                "success": True,
                "doc_id": doc_id,
                "response": response
            }

        except Exception as e:
            logger.error(f"❌ Failed to index document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def index_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        批量索引文档 - 使用正确的 SDK 方法

        Args:
            documents: 文档列表
            batch_size: 每批大小

        Returns:
            批量索引结果
        """
        logger.info(f"📚 Indexing {len(documents)} documents (batch size: {batch_size})")

        client = self._get_indexing_client()
        if not client:
            return {
                "success": False,
                "error": "Indexing client not available"
            }

        success_count = 0
        failure_count = 0
        results = {
            "total": len(documents),
            "success": success_count,
            "failure": failure_count,
            "errors": []
        }

        # 分批处理
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"📦 Processing batch {batch_num}/{(len(documents) - 1)//batch_size + 1}")

            try:
                # 构建文档定义列表 - 使用 SDK 模型
                doc_definitions = []
                for doc in batch:
                    # 构建 DocumentBody
                    mime_type = doc.get("mimeType", "text/html")
                    content = doc.get("content", "")

                    if mime_type.startswith("text/html"):
                        document_body = models.DocumentBody(
                            mime_type=mime_type,
                            html_content=content
                        )
                    else:
                        document_body = models.DocumentBody(
                            mime_type=mime_type,
                            text_content=content
                        )

                    # 构建 Document
                    doc_def = models.Document(
                        id=doc["id"],
                        title=doc["title"],
                        body=document_body,
                        view_url=doc.get("viewUrl"),
                        datasource=doc.get("datasource"),
                        container_id=doc.get("containerId") or doc.get("datasource"),
                        metadata=doc.get("metadata"),
                        updated_at=doc.get("updatedAt")
                    )

                    doc_definitions.append(doc_def)

                # 调用正确的批量索引 API: client.indexing.documents.bulk_index()
                response = client.indexing.documents.bulk_index(
                    documents=doc_definitions
                )

                batch_success = len(batch)
                success_count += batch_success
                logger.success(f"✅ Batch {batch_num} indexed {batch_success} documents")

            except Exception as e:
                logger.error(f"❌ Batch {batch_num} failed: {str(e)}")
                failure_count += len(batch)
                results["errors"].append({
                    "batch": batch_num,
                    "error": str(e)
                })

        results["success"] = success_count
        results["failure"] = failure_count

        logger.info(f"📊 Batch indexing complete: {success_count} succeeded, {failure_count} failed")
        return results
    
    def delete_document(
        self,
        datasource: str,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        删除文档 - 使用正确的 SDK 方法

        Args:
            datasource: 数据源名称
            doc_id: 文档 ID

        Returns:
            删除结果
        """
        logger.info(f"🗑️ Deleting document: {doc_id}")

        client = self._get_indexing_client()
        if not client:
            return {
                "success": False,
                "error": "Indexing client not available"
            }

        try:
            # 调用正确的删除 API: client.indexing.documents.delete()
            response = client.indexing.documents.delete(
                datasource=datasource,
                document_id=doc_id
            )

            logger.success(f"✅ Document '{doc_id}' deleted successfully")
            return {
                "success": True,
                "doc_id": doc_id,
                "response": response
            }

        except Exception as e:
            logger.error(f"❌ Failed to delete document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_document_count(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """
        获取文档计数
        
        Args:
            datasource: 数据源名称（可选）
            
        Returns:
            文档计数信息
        """
        logger.info(f"📊 Getting document count")
        
        client = self._get_indexing_client()
        if not client:
            return {
                "total": 0,
                "datasourceDocumentCounts": [],
                "error": "Indexing client not available"
            }
        
        url = glean_config.indexing_api_url + "/getdocumentcount"
        if datasource:
            url += f"?datasource={datasource}"
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {glean_config.indexing_api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"📊 Total documents: {data.get('totalDocumentCount', 0)}")
            
            if "datasourceDocumentCounts" in data:
                for ds in data["datasourceDocumentCounts"]:
                    logger.info(f"   - {ds['datasource']}: {ds['documentCount']}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get document count: {str(e)}")
            return {
                "total": 0,
                "datasourceDocumentCounts": [],
                "error": str(e)
            }
