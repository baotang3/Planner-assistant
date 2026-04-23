"""向量存储服务 - 用于景点知识库和用户偏好存储"""

import os
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from ..core.config import get_settings


class VectorStoreService:
    """向量存储服务"""

    def __init__(self):
        settings = get_settings()

        # 确保持久化目录存在
        persist_dir = settings.chroma_persist_directory
        os.makedirs(persist_dir, exist_ok=True)

        # 延迟初始化 embedding 和 vector store
        self._embeddings = None
        self._poi_store = None
        self._preference_store = None
        self._persist_dir = persist_dir
        self._settings = settings

    def _get_embeddings(self):
        """延迟初始化 embeddings"""
        if self._embeddings is None:
            from langchain_openai import OpenAIEmbeddings
            self._embeddings = OpenAIEmbeddings(
                model=self._settings.embedding_model,
                openai_api_key=self._settings.openai_api_key or self._settings.deepseek_api_key,
                openai_api_base=self._settings.openai_base_url if self._settings.openai_api_key else self._settings.deepseek_base_url
            )
        return self._embeddings

    def _get_poi_store(self):
        """延迟初始化 POI 向量存储"""
        if self._poi_store is None:
            from langchain_chroma import Chroma
            self._poi_store = Chroma(
                collection_name="poi_knowledge",
                embedding_function=self._get_embeddings(),
                persist_directory=self._persist_dir
            )
        return self._poi_store

    def _get_preference_store(self):
        """延迟初始化偏好向量存储"""
        if self._preference_store is None:
            from langchain_chroma import Chroma
            self._preference_store = Chroma(
                collection_name="user_preferences",
                embedding_function=self._get_embeddings(),
                persist_directory=self._persist_dir
            )
        return self._preference_store

    async def add_poi_knowledge(
        self,
        city: str,
        pois: List[Dict[str, Any]]
    ) -> None:
        """
        添加 POI 知识到向量库

        Args:
            city: 城市
            pois: POI 列表
        """
        documents = []
        for poi in pois:
            content = f"""
城市: {city}
景点名称: {poi.get('name', '')}
地址: {poi.get('address', '')}
类别: {poi.get('category', '')}
描述: {poi.get('description', '')}
坐标: {poi.get('location', {}).get('longitude', 0)}, {poi.get('location', {}).get('latitude', 0)}
"""
            documents.append(Document(
                page_content=content,
                metadata={
                    "city": city,
                    "poi_id": poi.get("id", ""),
                    "name": poi.get("name", ""),
                    "type": "poi"
                }
            ))

        if documents:
            self._get_poi_store().add_documents(documents)

    async def search_similar_pois(
        self,
        query: str,
        city: Optional[str] = None,
        k: int = 5
    ) -> List[Document]:
        """
        搜索相似的 POI

        Args:
            query: 查询文本
            city: 城市过滤
            k: 返回数量

        Returns:
            相似文档列表
        """
        filter_dict = None
        if city:
            filter_dict = {"city": city}

        return self._get_poi_store().similarity_search(
            query,
            k=k,
            filter=filter_dict
        )

    async def save_user_preference(
        self,
        user_id: str,
        preference_type: str,
        preference_data: Dict[str, Any]
    ) -> None:
        """
        保存用户偏好

        Args:
            user_id: 用户 ID
            preference_type: 偏好类型
            preference_data: 偏好数据
        """
        content = f"""
用户ID: {user_id}
偏好类型: {preference_type}
偏好数据: {preference_data}
"""
        self._get_preference_store().add_documents([
            Document(
                page_content=content,
                metadata={
                    "user_id": user_id,
                    "preference_type": preference_type,
                    "type": "preference"
                }
            )
        ])

    async def get_user_preferences(
        self,
        user_id: str,
        preference_type: Optional[str] = None
    ) -> List[Document]:
        """
        获取用户偏好

        Args:
            user_id: 用户 ID
            preference_type: 偏好类型过滤

        Returns:
            偏好文档列表
        """
        filter_dict = {"user_id": user_id}
        if preference_type:
            filter_dict["preference_type"] = preference_type

        return self._get_preference_store().get(where=filter_dict)


# 单例
_vector_store: Optional[VectorStoreService] = None


def get_vector_store() -> VectorStoreService:
    """获取向量存储服务实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
