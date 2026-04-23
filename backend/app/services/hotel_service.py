"""酒店搜索服务模块 - 封装酒店搜索和错误处理逻辑"""

from typing import List, Optional, Dict, Any
from ..models.schemas import Hotel
from ..core.exceptions import HotelSearchException, ValidationException
from ..core.logger import get_hotel_service_logger
from ..core.formatters import format_hotels
from .amap_service import get_amap_service


class HotelService:
    """酒店搜索服务"""

    def __init__(self):
        self.amap = get_amap_service()
        self.logger = get_hotel_service_logger()

    async def search_hotels_by_preference(
        self,
        city: str,
        accommodation_preference: str = "经济型酒店",
        max_results: int = 10
    ) -> List[Hotel]:
        """
        根据住宿偏好搜索酒店

        Args:
            city: 城市名称
            accommodation_preference: 住宿偏好（如"经济型酒店"、"舒适型酒店"等）
            max_results: 最大返回结果数量

        Returns:
            酒店列表

        Raises:
            ValidationException: 参数验证失败
            HotelSearchException: 酒店搜索失败
        """
        # 参数验证
        if not city or not city.strip():
            raise ValidationException("城市名称不能为空", field="city")

        if max_results <= 0:
            raise ValidationException(
                "最大结果数量必须大于0",
                field="max_results",
                value=max_results
            )

        if not accommodation_preference or not accommodation_preference.strip():
            accommodation_preference = "酒店"
            self.logger.warning("住宿偏好为空，使用默认值: '酒店'")

        self.logger.info(
            f"开始搜索酒店",
            city=city,
            accommodation_preference=accommodation_preference,
            max_results=max_results
        )

        try:
            hotels = await self.amap.search_hotels(city, accommodation_preference)
            self.logger.info(
                f"酒店搜索完成",
                city=city,
                found_hotels=len(hotels)
            )

            # 限制返回数量，避免响应过大
            if len(hotels) > max_results:
                original_count = len(hotels)
                hotels = hotels[:max_results]
                self.logger.debug(
                    f"限制返回酒店数量",
                    original_count=original_count,
                    limited_count=len(hotels),
                    max_results=max_results
                )

            return hotels

        except Exception as e:
            self.logger.exception(
                f"酒店搜索失败",
                exc=e,
                city=city,
                accommodation_preference=accommodation_preference
            )
            # 抛出业务异常而不是返回空列表
            raise HotelSearchException(
                f"酒店搜索失败: {str(e)}",
                city=city,
                hotel_type=accommodation_preference
            ) from e

    def format_hotels_for_prompt(self, hotels: List[Hotel], max_hotels: int = 5) -> str:
        """
        格式化酒店信息用于LLM提示词

        Args:
            hotels: 酒店列表
            max_hotels: 最大显示酒店数量

        Returns:
            格式化后的字符串
        """
        self.logger.debug(
            f"格式化酒店信息",
            hotels_count=len(hotels),
            max_hotels=max_hotels
        )
        return format_hotels(hotels, limit=max_hotels)

    def find_hotel_by_name(
        self,
        hotel_name: str,
        hotels: List[Hotel],
        case_sensitive: bool = False
    ) -> Optional[Hotel]:
        """
        根据名称查找酒店

        Args:
            hotel_name: 酒店名称
            hotels: 酒店列表
            case_sensitive: 是否区分大小写

        Returns:
            匹配的酒店或None
        """
        if not hotel_name or not hotel_name.strip():
            self.logger.warning("查找酒店时名称为空")
            return None

        if not hotels:
            self.logger.debug("在空酒店列表中查找", hotel_name=hotel_name)
            return None

        search_name = hotel_name if case_sensitive else hotel_name.lower()
        self.logger.debug(
            f"查找酒店",
            hotel_name=hotel_name,
            hotels_count=len(hotels),
            case_sensitive=case_sensitive
        )

        for hotel in hotels:
            hotel_name_to_compare = hotel.name if case_sensitive else hotel.name.lower()

            # 精确匹配
            if hotel_name_to_compare == search_name:
                self.logger.debug(f"精确匹配找到酒店", hotel_name=hotel_name)
                return hotel

            # 包含匹配（不区分大小写时）
            if not case_sensitive and search_name in hotel_name_to_compare:
                self.logger.debug(f"包含匹配找到酒店", hotel_name=hotel_name)
                return hotel

        self.logger.debug(f"未找到匹配的酒店", hotel_name=hotel_name)
        return None


# 单例实例
_hotel_service: Optional[HotelService] = None


def get_hotel_service() -> HotelService:
    """获取酒店服务实例"""
    global _hotel_service
    if _hotel_service is None:
        _hotel_service = HotelService()
    return _hotel_service