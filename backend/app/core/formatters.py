"""共享格式化工具模块

提供统一的格式化函数，消除代码重复。
"""

from typing import List, Optional
from ..models.schemas import POI, Weather, Hotel


def format_pois(pois: List[POI], limit: Optional[int] = 15) -> str:
    """
    格式化POI信息用于提示词

    Args:
        pois: POI列表
        limit: 最大显示数量，None表示无限制

    Returns:
        格式化后的字符串
    """
    if not pois:
        return "暂无景点信息"

    lines = []
    display_pois = pois[:limit] if limit else pois

    for i, poi in enumerate(display_pois, 1):
        lines.append(f"{i}. {poi.name}")
        lines.append(f"   地址: {poi.address}")

        if poi.location:
            lines.append(f"   坐标: ({poi.location.longitude}, {poi.location.latitude})")
        else:
            lines.append(f"   坐标: 未知")

        if poi.rating:
            lines.append(f"   评分: {poi.rating}")

        lines.append("")

    return "\n".join(lines)


def format_weather(weather_data: List[Weather], limit: Optional[int] = None) -> str:
    """
    格式化天气信息用于提示词

    Args:
        weather_data: 天气信息列表
        limit: 最大显示天数，None表示无限制

    Returns:
        格式化后的字符串
    """
    if not weather_data:
        return "暂无天气信息"

    lines = []
    display_weather = weather_data[:limit] if limit else weather_data

    for weather in display_weather:
        lines.append(
            f"{weather.date}: {weather.day_weather} {weather.day_temp}°C / "
            f"{weather.night_weather} {weather.night_temp}°C"
        )

    return "\n".join(lines)


def format_hotels(hotels: List[Hotel], limit: Optional[int] = 5) -> str:
    """
    格式化酒店信息用于提示词

    Args:
        hotels: 酒店列表
        limit: 最大显示数量，None表示无限制

    Returns:
        格式化后的字符串
    """
    if not hotels:
        return "暂无酒店信息"

    lines = []
    display_hotels = hotels[:limit] if limit else hotels

    for i, hotel in enumerate(display_hotels, 1):
        lines.append(f"{i}. {hotel.name} - {hotel.address}")
        if hotel.rating:
            lines.append(f"   评分: {hotel.rating}")

    return "\n".join(lines)


def format_pois_for_debug(pois: List[POI], limit: int = 10) -> str:
    """
    格式化POI信息用于调试（更详细的信息）

    Args:
        pois: POI列表
        limit: 最大显示数量

    Returns:
        格式化后的调试信息
    """
    if not pois:
        return "无POI数据"

    lines = [f"共找到 {len(pois)} 个POI:"]

    for i, poi in enumerate(pois[:limit], 1):
        lines.append(f"{i}. {poi.name}")
        lines.append(f"   地址: {poi.address}")
        lines.append(f"   类别: {poi.category}")

        if poi.location:
            lines.append(f"   坐标: ({poi.location.longitude:.6f}, {poi.location.latitude:.6f})")

        if poi.rating:
            lines.append(f"   评分: {poi.rating}")

        if poi.tel:
            lines.append(f"   电话: {poi.tel}")

        lines.append("")

    if len(pois) > limit:
        lines.append(f"... 还有 {len(pois) - limit} 个POI未显示")

    return "\n".join(lines)


def format_location(location) -> str:
    """
    格式化位置信息

    Args:
        location: 位置对象或字典

    Returns:
        格式化后的坐标字符串
    """
    if not location:
        return "未知位置"

    if hasattr(location, 'longitude') and hasattr(location, 'latitude'):
        return f"({location.longitude:.6f}, {location.latitude:.6f})"
    elif isinstance(location, dict):
        lng = location.get('longitude') or location.get('lng')
        lat = location.get('latitude') or location.get('lat')
        if lng and lat:
            return f"({float(lng):.6f}, {float(lat):.6f})"

    return "无效位置"