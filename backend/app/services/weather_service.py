"""天气查询服务模块 - 封装天气查询和格式化逻辑"""

from typing import List, Optional, Dict, Any
from ..models.schemas import Weather
from ..core.exceptions import WeatherQueryException, ValidationException
from ..core.logger import get_weather_service_logger
from ..core.formatters import format_weather
from .amap_service import get_amap_service


class WeatherService:
    """天气查询服务"""

    def __init__(self):
        self.amap = get_amap_service()
        self.logger = get_weather_service_logger()

    async def get_weather_forecast(self, city: str, forecast_days: int = 7) -> List[Weather]:
        """
        获取天气预报

        Args:
            city: 城市名称
            forecast_days: 预报天数（高德地图通常返回4-7天）

        Returns:
            天气信息列表

        Raises:
            ValidationException: 参数验证失败
            WeatherQueryException: 天气查询失败
        """
        # 参数验证
        if not city or not city.strip():
            raise ValidationException("城市名称不能为空", field="city")

        if forecast_days <= 0:
            raise ValidationException(
                "预报天数必须大于0",
                field="forecast_days",
                value=forecast_days
            )

        self.logger.info(f"开始查询天气", city=city, forecast_days=forecast_days)

        try:
            weather_data = await self.amap.get_weather(city)
            self.logger.info(
                f"天气查询完成",
                city=city,
                forecast_days=len(weather_data)
            )

            # 限制返回天数
            if len(weather_data) > forecast_days:
                original_count = len(weather_data)
                weather_data = weather_data[:forecast_days]
                self.logger.debug(
                    f"限制返回天气天数",
                    original_count=original_count,
                    limited_count=len(weather_data),
                    forecast_days=forecast_days
                )

            return weather_data

        except Exception as e:
            self.logger.exception(
                f"天气查询失败",
                exc=e,
                city=city
            )
            # 抛出业务异常而不是返回空列表
            raise WeatherQueryException(
                f"天气查询失败: {str(e)}",
                city=city
            ) from e

    def format_weather_for_prompt(self, weather_data: List[Weather]) -> str:
        """
        格式化天气信息用于LLM提示词

        Args:
            weather_data: 天气信息列表

        Returns:
            格式化后的字符串
        """
        self.logger.debug(
            f"格式化天气信息",
            weather_days=len(weather_data)
        )
        return format_weather(weather_data)

    def get_weather_for_date(
        self,
        weather_data: List[Weather],
        date: str,
        return_default: bool = True
    ) -> Optional[Weather]:
        """
        获取指定日期的天气信息

        Args:
            weather_data: 天气信息列表
            date: 日期字符串 (YYYY-MM-DD)
            return_default: 未找到时是否返回默认值

        Returns:
            天气信息，如果未找到则根据return_default参数返回默认值或None
        """
        if not weather_data:
            self.logger.warning("天气数据为空", date=date)
            if return_default:
                return self._create_default_weather(date)
            return None

        if not date or not date.strip():
            self.logger.warning("查询日期为空")
            if return_default:
                return self._create_default_weather("未知日期")
            return None

        self.logger.debug(f"查找指定日期天气", date=date, weather_days=len(weather_data))

        for weather in weather_data:
            if weather.date == date:
                self.logger.debug(f"找到指定日期天气", date=date)
                return weather

        self.logger.warning(f"未找到指定日期天气", date=date, available_dates=[w.date for w in weather_data])

        if return_default:
            self.logger.debug(f"返回默认天气信息", date=date)
            return self._create_default_weather(date)

        return None

    def _create_default_weather(self, date: str) -> Weather:
        """创建默认天气信息"""
        return Weather(
            date=date,
            day_weather="未知",
            night_weather="未知",
            day_temp=0,
            night_temp=0,
            wind_direction="未知",
            wind_power="未知"
        )


# 单例实例
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """获取天气服务实例"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service