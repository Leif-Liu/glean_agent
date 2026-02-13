"""
数据源管理模块 - 管理自定义数据源和索引任务
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from config.config import glean_config


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
        创建数据源
        
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
        
        payload = {
            "name": name,
            "displayName": display_name or name.replace("-", " ").title(),
            "datasourceCategory": category,
            "isUserReferencedByEmail": is_user_referenced_by_email
        }
        
        if url_regex:
            payload["urlRegex"] = url_regex
        
        try:
            # 调用 Glean Indexing API
            response = client.indexing.add_datasource(datasource=payload)
            
            if hasattr(response, 'status_code') and response.status_code in [200, 201]:
                logger.success(f"✅ Datasource '{name}' created successfully")
                return {
                    "success": True,
                    "datasource_id": name,
                    "response": response.data if hasattr(response, 'data') else None
                }
            else:
                logger.warning(f"⚠️ Unexpected status: {getattr(response, 'status_code', 'unknown')}")
                return {
                    "success": False,
                    "error": f"Unexpected status: {getattr(response, 'status_code', 'unknown')}"
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
        updated_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        索引单个文档
        
        Args:
            datasource: 数据源名称
            doc_id: 文档唯一 ID
            title: 文档标题
            body: 文档内容
            view_url: 查看 URL
            metadata: 元数据
            mime_type: MIME 类型
            updated_at: 更新时间
            
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
        
        # 构建文档定义
        document_body = {
            "mimeType": mime_type,
            "textContent": body
        }
        
        document = {
            "id": doc_id,
            "title": title,
            "body": document_body,
            "viewUrl": view_url,
            "datasource": datasource
        }
        
        # 添加元数据
        if metadata:
            document["metadata"] = metadata
        
        if updated_at:
            document["updatedAt"] = updated_at
        
        try:
            # 调用索引 API
            response = client.indexing.index_document(document=document)
            
            if hasattr(response, 'status_code') and response.status_code in [200, 201]:
                logger.success(f"✅ Document '{doc_id}' indexed successfully")
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "response": response.data if hasattr(response, 'data') else None
                }
            else:
                logger.warning(f"⚠️ Unexpected status: {getattr(response, 'status_code', 'unknown')}")
                return {
                    "success": False,
                    "error": f"Unexpected status: {getattr(response, 'status_code', 'unknown')}"
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
        批量索引文档
        
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
                # 构建文档定义列表
                doc_definitions = []
                for doc in batch:
                    document_body = {
                        "mimeType": doc.get("mimeType", "text/html"),
                        "textContent": doc.get("content", "")
                    }
                    
                    doc_def = {
                        "id": doc["id"],
                        "title": doc["title"],
                        "body": document_body,
                        "viewUrl": doc.get("viewUrl"),
                        "datasource": doc.get("datasource")
                    }
                    
                    if "metadata" in doc:
                        doc_def["metadata"] = doc["metadata"]
                    
                    doc_definitions.append(doc_def)
                
                # 调用批量索引 API
                response = client.indexing.index_documents(documents=doc_definitions)
                
                if hasattr(response, 'status_code') and response.status_code in [200, 201]:
                    batch_success = len(batch)
                    success_count += batch_success
                    logger.success(f"✅ Batch {batch_num} indexed {batch_success} documents")
                else:
                    logger.warning(f"⚠️ Batch {batch_num} failed with status: {getattr(response, 'status_code', 'unknown')}")
                    failure_count += len(batch)
                    results["errors"].append({
                        "batch": batch_num,
                        "status": getattr(response, 'status_code', 'unknown'),
                        "error": "Indexing failed"
                    })
                    
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
        删除文档
        
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
            response = client.indexing.delete_document(
                datasource=datasource,
                documentId=doc_id
            )
            
            if hasattr(response, 'status_code') and response.status_code in [200, 204]:
                logger.success(f"✅ Document '{doc_id}' deleted successfully")
                return {
                    "success": True,
                    "doc_id": doc_id
                }
            else:
                logger.warning(f"⚠️ Unexpected status: {getattr(response, 'status_code', 'unknown')}")
                return {
                    "success": False,
                    "error": f"Unexpected status: {getattr(response, 'status_code', 'unknown')}"
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
