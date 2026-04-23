"""行程规划协调服务 - 整合所有服务，提供完整的行程规划功能"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from ..models.schemas import TripRequest, POI, Hotel, Weather
from ..core.exceptions import TripPlannerException, ValidationException
from ..core.logger import get_trip_coordinator_logger
from .poi_service import get_poi_service
from .hotel_service import get_hotel_service
from .weather_service import get_weather_service
from .llm_service import get_llm_service


class TripCoordinator:
    """行程规划协调器"""

    def __init__(self):
        self.poi_service = get_poi_service()
        self.hotel_service = get_hotel_service()
        self.weather_service = get_weather_service()
        self.llm_service = get_llm_service()
        self.logger = get_trip_coordinator_logger()

    async def plan_trip_sync(self, request: TripRequest) -> Dict[str, Any]:
        """
        同步行程规划

        Args:
            request: 旅行请求

        Returns:
            行程规划结果
        """
        self.logger.info(
            f"开始同步行程规划",
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            travel_days=request.travel_days,
            llm_provider=request.llm_provider or "deepseek"
        )

        try:
            # 1. 并行获取所有数据
            self.logger.debug("Step 1: 并行获取数据...")
            pois, hotels, weather = await self._gather_all_data(request)

            # 2. 构建提示词
            self.logger.debug("Step 2: 构建提示词...")
            prompt = self._build_prompt(request, pois, hotels, weather)

            # 3. 调用LLM
            self.logger.debug("Step 3: 调用LLM...")
            llm_provider = request.llm_provider or "deepseek"
            llm_response = await self.llm_service.generate_trip_plan(prompt, llm_provider)

            # 4. 解析响应
            self.logger.debug("Step 4: 解析LLM响应...")
            trip_plan = self.llm_service.parse_llm_response(
                llm_response, request, pois, hotels, weather
            )

            self.logger.info(f"解析成功，共 {len(trip_plan.get('days', []))} 天行程")

            # 5. 记录解析后的数据
            self._log_parsed_plan(trip_plan)

            return trip_plan

        except Exception as e:
            self.logger.exception(f"行程规划失败", exc=e)
            raise

    async def plan_trip_stream(
        self,
        request: TripRequest,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        流式行程规划（支持进度回调）

        Args:
            request: 旅行请求
            progress_callback: 进度回调函数

        Returns:
            行程规划结果
        """
        try:
            # Step 1: 初始化
            self._notify_progress(progress_callback, 1, "init", "running", "正在初始化...")

            # Step 2: 并行获取所有数据
            self._notify_progress(progress_callback, 2, "data_gathering", "running",
                                  "正在获取旅行数据...")

            pois, hotels, weather = await self._gather_all_data_with_progress(
                request, progress_callback
            )

            # Step 3: 构建提示词
            self._notify_progress(progress_callback, 3, "prompt_building", "running",
                                  "正在构建行程规划提示词...")

            prompt = self._build_prompt(request, pois, hotels, weather)

            # Step 4: 调用LLM
            self._notify_progress(progress_callback, 4, "llm_generation", "running",
                                  f"正在调用 {request.llm_provider or 'deepseek'} 生成行程规划...")

            llm_provider = request.llm_provider or "deepseek"
            llm_response = await self.llm_service.generate_trip_plan(prompt, llm_provider)

            # Step 5: 解析响应
            self._notify_progress(progress_callback, 5, "response_parsing", "running",
                                  "正在解析 AI 响应...")

            trip_plan = self.llm_service.parse_llm_response(
                llm_response, request, pois, hotels, weather
            )

            self._notify_progress(progress_callback, 5, "response_parsing", "completed",
                                  f"行程规划完成，共 {len(trip_plan.get('days', []))} 天行程",
                                  {"plan_generated": True, "days_count": len(trip_plan.get('days', []))})

            return trip_plan

        except Exception as e:
            self._notify_progress(progress_callback, 0, "error", "failed",
                                  f"执行失败: {str(e)}")
            raise

    async def _gather_all_data(
        self,
        request: TripRequest
    ) -> tuple[List[POI], List[Hotel], List[Weather]]:
        """并行获取所有数据"""
        tasks = [
            self.poi_service.search_pois_by_keywords(request.preferences, request.city),
            self.hotel_service.search_hotels_by_preference(request.city, request.accommodation),
            self.weather_service.get_weather_forecast(request.city)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        pois = results[0] if not isinstance(results[0], Exception) else []
        hotels = results[1] if not isinstance(results[1], Exception) else []
        weather = results[2] if not isinstance(results[2], Exception) else []

        return pois, hotels, weather

    async def _gather_all_data_with_progress(
        self,
        request: TripRequest,
        progress_callback: Optional[Callable]
    ) -> tuple[List[POI], List[Hotel], List[Weather]]:
        """并行获取所有数据（带进度通知）"""
        # POI搜索
        self._notify_progress(progress_callback, 2, "poi_search", "running",
                              f"正在搜索景点: {', '.join(request.preferences[:3] if request.preferences else ['景点'])}...")

        pois_task = self.poi_service.search_pois_by_keywords(request.preferences, request.city)

        # 酒店搜索
        self._notify_progress(progress_callback, 2, "hotel_search", "running",
                              f"正在搜索{request.accommodation}...")

        hotels_task = self.hotel_service.search_hotels_by_preference(request.city, request.accommodation)

        # 天气查询
        self._notify_progress(progress_callback, 2, "weather_query", "running",
                              "正在查询天气预报...")

        weather_task = self.weather_service.get_weather_forecast(request.city)

        # 等待所有任务完成
        results = await asyncio.gather(pois_task, hotels_task, weather_task, return_exceptions=True)

        # 处理结果并通知进度
        pois = results[0] if not isinstance(results[0], Exception) else []
        hotels = results[1] if not isinstance(results[1], Exception) else []
        weather = results[2] if not isinstance(results[2], Exception) else []

        self._notify_progress(progress_callback, 2, "poi_search", "completed",
                              f"景点搜索完成，共找到 {len(pois)} 个景点",
                              {"pois_count": len(pois)})

        self._notify_progress(progress_callback, 2, "hotel_search", "completed",
                              f"酒店搜索完成，找到 {len(hotels)} 家酒店",
                              {"hotels_count": len(hotels)})

        self._notify_progress(progress_callback, 2, "weather_query", "completed",
                              f"天气查询完成，获取到 {len(weather)} 天预报",
                              {"weather_days": len(weather)})

        return pois, hotels, weather

    def _build_prompt(
        self,
        request: TripRequest,
        pois: List[POI],
        hotels: List[Hotel],
        weather: List[Weather]
    ) -> str:
        """构建提示词"""
        # 格式化POI信息
        pois_info = self._format_pois_for_prompt(pois[:15])

        # 格式化天气信息
        weather_info = self.weather_service.format_weather_for_prompt(weather)

        # 格式化酒店信息
        hotels_info = self.hotel_service.format_hotels_for_prompt(hotels[:5])

        # 偏好字符串
        preferences_str = ', '.join(request.preferences) if request.preferences else '无特殊偏好'
        extra_requirements = request.free_text_input or '无'

        # 构建提示词
        prompt = self.llm_service.build_trip_planning_prompt(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            travel_days=request.travel_days,
            transportation=request.transportation,
            accommodation=request.accommodation,
            preferences=preferences_str,
            extra_requirements=extra_requirements,
            pois_info=pois_info,
            weather_info=weather_info,
            hotels_info=hotels_info,
            budget_range=request.budget
        )

        return prompt

    def _format_pois_for_prompt(self, pois: List[POI]) -> str:
        """格式化POI信息用于提示词"""
        if not pois:
            return "暂无景点信息"

        lines = []
        for i, poi in enumerate(pois, 1):
            lines.append(f"{i}. {poi.name}")
            lines.append(f"   地址: {poi.address}")
            if poi.location:
                lines.append(f"   坐标: longitude={poi.location.longitude}, latitude={poi.location.latitude}")
            if poi.rating:
                lines.append(f"   评分: {poi.rating}")
            lines.append("")

        return "\n".join(lines)

    def _log_parsed_plan(self, trip_plan: Dict[str, Any]) -> None:
        """记录解析后的行程数据"""
        self.logger.debug(f"解析后的行程数据:")
        self.logger.debug(f"城市: {trip_plan.get('city')}")
        self.logger.debug(f"日期: {trip_plan.get('start_date')} ~ {trip_plan.get('end_date')}")
        for i, day in enumerate(trip_plan.get('days', [])):
            self.logger.debug(f"第{i+1}天: {day.get('date')}, {len(day.get('attractions', []))} 个景点")
            for j, attr in enumerate(day.get('attractions', [])):
                loc = attr.get('location', {})
                self.logger.debug(f"   景点[{j+1}]: {attr.get('name')} @ ({loc.get('longitude')}, {loc.get('latitude')})")

    def _notify_progress(
        self,
        callback: Optional[Callable],
        step: int,
        node: str,
        status: str,
        message: str,
        data: Optional[Dict] = None
    ) -> None:
        """通知进度"""
        if callback:
            try:
                callback(step, node, status, message, data or {})
            except Exception as e:
                self.logger.exception(f"进度回调失败", exc=e)


# 单例实例
_trip_coordinator: Optional[TripCoordinator] = None


def get_trip_coordinator() -> TripCoordinator:
    """获取行程规划协调器实例"""
    global _trip_coordinator
    if _trip_coordinator is None:
        _trip_coordinator = TripCoordinator()
    return _trip_coordinator