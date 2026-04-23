"""POI搜索服务模块 - 封装POI搜索、去重和错误处理逻辑"""

import asyncio
from typing import List, Optional, Dict, Any
from ..models.schemas import POI
from ..core.exceptions import POISearchException, ValidationException
from ..core.logger import get_poi_service_logger
from .amap_service import get_amap_service


class POIService:
    """POI搜索服务"""

    def __init__(self):
        self.amap = get_amap_service()
        self.logger = get_poi_service_logger()

    async def search_pois_by_keywords(
        self,
        keywords: List[str],
        city: str,
        max_keywords: int = 3
    ) -> List[POI]:
        """
        根据多个关键词搜索POI，支持并行搜索

        Args:
            keywords: 搜索关键词列表
            city: 城市名称
            max_keywords: 最大关键词数量限制

        Returns:
            POI列表

        Raises:
            ValidationException: 参数验证失败
            POISearchException: POI搜索失败
        """
        # 参数验证
        if not city or not city.strip():
            raise ValidationException("城市名称不能为空", field="city")

        if max_keywords <= 0:
            raise ValidationException(
                "最大关键词数量必须大于0",
                field="max_keywords",
                value=max_keywords
            )

        if not keywords:
            keywords = ["景点"]
            self.logger.info("未提供关键词，使用默认关键词: '景点'")

        # 限制关键词数量
        search_keywords = keywords[:max_keywords]
        self.logger.info(
            f"开始搜索POI: 城市={city}, 关键词={search_keywords}, 最大关键词数={max_keywords}"
        )

        # 并行搜索所有关键词
        tasks = []
        for keyword in search_keywords:
            task = self._search_single_keyword(keyword, city)
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果并处理异常
        all_pois = []
        failed_keywords = []

        for i, result in enumerate(results):
            keyword = search_keywords[i]
            if isinstance(result, Exception):
                self.logger.error(
                    f"关键词搜索失败",
                    keyword=keyword,
                    error=str(result)
                )
                failed_keywords.append(keyword)
                continue
            all_pois.extend(result)

        # 如果所有关键词都搜索失败，抛出异常
        if failed_keywords and len(failed_keywords) == len(search_keywords):
            raise POISearchException(
                f"所有关键词搜索失败: {failed_keywords}",
                keyword=",".join(failed_keywords),
                city=city,
                extra_data={"failed_keywords": failed_keywords}
            )

        # 去重
        unique_pois = self._deduplicate_pois(all_pois)

        self.logger.info(
            f"POI搜索完成",
            city=city,
            total_keywords=len(search_keywords),
            failed_keywords=len(failed_keywords),
            found_pois=len(all_pois),
            unique_pois=len(unique_pois)
        )

        if failed_keywords:
            self.logger.warning(
                f"部分关键词搜索失败",
                failed_keywords=failed_keywords
            )

        return unique_pois

    async def _search_single_keyword(self, keyword: str, city: str) -> List[POI]:
        """搜索单个关键词"""
        try:
            self.logger.debug(f"正在搜索关键词", keyword=keyword, city=city)
            pois = await self.amap.search_poi(keyword, city, citylimit=True)
            self.logger.debug(f"关键词搜索完成", keyword=keyword, found_pois=len(pois))
            return pois
        except Exception as e:
            self.logger.exception(f"关键词搜索失败", exc=e, keyword=keyword, city=city)
            # 重新抛出异常，让上层处理
            raise POISearchException(
                f"关键词 '{keyword}' 搜索失败: {str(e)}",
                keyword=keyword,
                city=city
            ) from e

    def _deduplicate_pois(self, pois: List[POI]) -> List[POI]:
        """
        去重POI列表（按名称）

        Args:
            pois: POI列表

        Returns:
            去重后的POI列表
        """
        if not pois:
            return []

        seen = set()
        unique_pois = []
        duplicate_count = 0

        for poi in pois:
            if poi.name not in seen:
                seen.add(poi.name)
                unique_pois.append(poi)
            else:
                duplicate_count += 1

        if duplicate_count > 0:
            self.logger.debug(
                f"POI去重完成",
                original_count=len(pois),
                unique_count=len(unique_pois),
                duplicate_count=duplicate_count
            )

        return unique_pois

    def build_poi_index(self, pois: List[POI]) -> Dict[str, POI]:
        """
        构建POI名称索引，用于快速匹配

        Args:
            pois: POI列表

        Returns:
            索引字典 {poi_name_lower: poi, ...}
        """
        if not pois:
            self.logger.debug("构建空POI索引")
            return {}

        index: Dict[str, POI] = {}
        total_entries = 0

        for poi in pois:
            # 主名称索引
            index[poi.name.lower()] = poi
            total_entries += 1

            # 别名或部分匹配（忽略短词）
            words = poi.name.lower().split()
            for word in words:
                if len(word) > 2:  # 忽略长度小于3的词
                    index[word] = poi
                    total_entries += 1

        self.logger.debug(
            f"POI索引构建完成",
            pois_count=len(pois),
            index_size=total_entries,
            avg_entries_per_poi=total_entries / len(pois) if pois else 0
        )

        return index

    def find_poi_by_name(
        self,
        poi_name: str,
        pois: List[POI],
        use_index: bool = True
    ) -> Optional[POI]:
        """
        根据名称查找POI，支持模糊匹配

        Args:
            poi_name: 要查找的POI名称
            pois: POI列表
            use_index: 是否使用索引加速查找（对于大型列表推荐）

        Returns:
            匹配的POI或None
        """
        if not poi_name or not poi_name.strip():
            self.logger.warning("查找POI时名称为空")
            return None

        if not pois:
            self.logger.debug("在空POI列表中查找", poi_name=poi_name)
            return None

        poi_name_lower = poi_name.lower().strip()
        self.logger.debug(
            f"查找POI",
            poi_name=poi_name,
            pois_count=len(pois),
            use_index=use_index
        )

        if use_index and len(pois) > 10:
            # 对于大型列表，使用索引加速
            index = self.build_poi_index(pois)

            # 1. 精确匹配
            matched_poi = index.get(poi_name_lower)
            if matched_poi:
                self.logger.debug(f"通过索引精确匹配找到POI", poi_name=poi_name)
                return matched_poi

            # 2. 部分匹配（检查POI名称中的单词）
            words = poi_name_lower.split()
            for word in words:
                if len(word) > 2 and word in index:
                    self.logger.debug(f"通过索引部分匹配找到POI", poi_name=poi_name, matched_word=word)
                    return index[word]
        else:
            # 小列表直接线性搜索
            # 精确匹配
            for poi in pois:
                if poi.name.lower() == poi_name_lower:
                    self.logger.debug(f"精确匹配找到POI", poi_name=poi_name)
                    return poi

            # 包含匹配
            for poi in pois:
                if poi_name_lower in poi.name.lower() or poi.name.lower() in poi_name_lower:
                    self.logger.debug(f"包含匹配找到POI", poi_name=poi_name)
                    return poi

        self.logger.debug(f"未找到匹配的POI", poi_name=poi_name)
        return None


# 单例实例
_poi_service: Optional[POIService] = None


def get_poi_service() -> POIService:
    """获取POI服务实例"""
    global _poi_service
    if _poi_service is None:
        _poi_service = POIService()
    return _poi_service