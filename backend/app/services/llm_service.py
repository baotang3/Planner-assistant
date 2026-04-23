"""LLM服务模块 - 封装提示词构建、LLM调用和响应解析逻辑"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from ..models.schemas import TripRequest, POI, Hotel, Weather
from ..core.llm import get_llm, invoke_llm_with_logging
from ..core.logger import get_llm_service_logger


class LLMService:
    """LLM服务"""

    def __init__(self):
        self.logger = get_llm_service_logger()

    def build_trip_planning_prompt(
        self,
        city: str,
        start_date: str,
        end_date: str,
        travel_days: int,
        transportation: str,
        accommodation: str,
        preferences: str,
        extra_requirements: str,
        pois_info: str,
        weather_info: str,
        hotels_info: str,
        budget_range: Optional[List[int]] = None
    ) -> str:
        """
        构建旅行规划提示词

        Args:
            所有旅行规划相关参数

        Returns:
            格式化后的提示词
        """
        # 预算信息
        budget_str = "无预算限制"
        budget_hint = ""
        if budget_range and len(budget_range) == 2:
            min_budget, max_budget = budget_range
            budget_str = f"{min_budget} - {max_budget} 元"
            # 根据预算给出提示
            if max_budget <= 1500:
                budget_hint = "\n注意：用户预算较紧张，请推荐免费或低价景点，选择经济实惠的餐饮和住宿。"
            elif max_budget <= 3000:
                budget_hint = "\n注意：用户预算适中，请合理安排景点门票，餐饮选择性价比高的餐厅。"
            elif max_budget <= 5000:
                budget_hint = "\n注意：用户预算充足，可以安排一些特色体验和品质餐饮。"
            else:
                budget_hint = "\n注意：用户预算宽裕，可以推荐高品质酒店和特色景点。"

        prompt = f"""你是一个专业的旅行规划师。请根据以下信息生成一份详细的旅行计划。

## 基本信息
- 城市: {city}
- 日期范围: {start_date} 至 {end_date}
- 旅行天数: {travel_days} 天
- 交通方式: {transportation}
- 住宿偏好: {accommodation}
- 用户偏好: {preferences}
- 预算范围: {budget_str}
- 额外要求: {extra_requirements}{budget_hint}

## 可用景点 (请使用这些真实景点)
{pois_info}

## 天气预报
{weather_info}

## 可用酒店
{hotels_info}

## 任务要求
1. 从可用景点中选择合适的景点，每天安排 2-3 个
2. 使用景点列表中提供的真实坐标 (longitude, latitude)
3. 为每天安排早餐、午餐、晚餐，价格要合理
4. 推荐合适的酒店，价格要在预算范围内
5. 生成的总预算必须严格控制在用户预算范围内
6. 门票、餐饮、住宿价格要参考实际情况，不要过高

请严格按照以下 JSON 格式输出，不要添加任何其他内容:

```json
{{
  "city": "城市名",
  "start_date": "开始日期",
  "end_date": "结束日期",
  "days": [
    {{
      "date": "日期YYYY-MM-DD",
      "day_index": 0,
      "description": "当日行程描述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {{
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {{"longitude": 0, "latitude": 0}},
        "price_range": "价格范围",
        "rating": "评分",
        "type": "酒店类型",
        "estimated_cost": 200
      }},
      "attractions": [
        {{
          "name": "景点名称",
          "address": "景点地址",
          "location": {{"longitude": 116.4, "latitude": 39.9}},
          "visit_duration": 120,
          "description": "景点描述",
          "category": "景点类别",
          "ticket_price": 50
        }}
      ],
      "meals": [
        {{"type": "breakfast", "name": "早餐", "description": "描述", "estimated_cost": 20}},
        {{"type": "lunch", "name": "午餐", "description": "描述", "estimated_cost": 40}},
        {{"type": "dinner", "name": "晚餐", "description": "描述", "estimated_cost": 60}}
      ]
    }}
  ],
  "weather_info": [],
  "overall_suggestions": "总体建议",
  "budget": {{
    "total_attractions": 150,
    "total_hotels": 400,
    "total_meals": 300,
    "total_transportation": 50,
    "total": 900
  }}
}}
"""
        return prompt

    async def generate_trip_plan(
        self,
        prompt: str,
        llm_provider: str = "deepseek"
    ) -> str:
        """
        调用LLM生成旅行计划

        Args:
            prompt: 提示词
            llm_provider: LLM提供商

        Returns:
            LLM响应文本
        """
        try:
            llm = get_llm(llm_provider)
            response = await invoke_llm_with_logging(llm, prompt, llm_provider)
            return response
        except Exception as e:
            self.logger.exception(f"LLM调用失败", exc=e)
            raise

    def parse_llm_response(
        self,
        response: str,
        request: TripRequest,
        pois: List[POI],
        hotels: List[Hotel],
        weather: List[Weather]
    ) -> Dict[str, Any]:
        """
        解析LLM响应

        Args:
            response: LLM响应文本
            request: 旅行请求
            pois: POI列表
            hotels: 酒店列表
            weather: 天气列表

        Returns:
            解析后的行程数据
        """
        try:
            json_str = self._extract_json_from_response(response)
            data = json.loads(json_str)

            # 确保必要字段存在
            if "city" not in data:
                data["city"] = request.city
            if "start_date" not in data:
                data["start_date"] = request.start_date
            if "end_date" not in data:
                data["end_date"] = request.end_date
            if "days" not in data or not data["days"]:
                data["days"] = self._create_default_days(request, pois)

            # 为景点添加坐标
            data = self._enrich_with_poi_coordinates(data, pois)

            return data

        except json.JSONDecodeError as e:
            self.logger.exception(f"JSON解析失败", exc=e)
            self.logger.debug(f"原始响应: {response[:1000]}")
            return self._create_fallback_plan(request, pois, hotels, weather)

    def _extract_json_from_response(self, response: str) -> str:
        """从响应中提取JSON字符串"""
        json_str = response

        # 尝试从markdown代码块中提取
        if "```json" in response:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if match:
                json_str = match.group(1)
        elif "```" in response:
            match = re.search(r'```\s*([\s\S]*?)\s*```', response)
            if match:
                json_str = match.group(1)

        # 查找JSON对象
        start = json_str.find("{")
        if start >= 0:
            brace_count = 0
            end = start
            for i, char in enumerate(json_str[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            json_str = json_str[start:end]

        return json_str

    def _enrich_with_poi_coordinates(
        self,
        data: Dict[str, Any],
        pois: List[POI]
    ) -> Dict[str, Any]:
        """为景点添加坐标"""
        self.logger.debug(f"开始处理景点坐标...")
        self.logger.debug(f"可用POI数量: {len(pois)}")

        # 构建POI索引
        poi_index = {}
        for poi in pois:
            poi_index[poi.name.lower()] = poi
            # 添加部分匹配
            words = poi.name.lower().split()
            for word in words:
                if len(word) > 2:
                    poi_index[word] = poi

        for day_idx, day in enumerate(data.get("days", [])):
            self.logger.debug(f"处理第{day_idx + 1}天景点...")
            for attr_idx, attr in enumerate(day.get("attractions", [])):
                attr_name = attr.get("name", "未知")
                self.logger.debug(f"景点[{attr_idx}]: {attr_name}")

                if "location" not in attr or not attr["location"]:
                    # 尝试从POI索引中匹配
                    matched_poi = poi_index.get(attr_name.lower())
                    if not matched_poi:
                        # 尝试模糊匹配
                        for poi in pois:
                            if (attr_name.lower() in poi.name.lower() or
                                poi.name.lower() in attr_name.lower()):
                                matched_poi = poi
                                break

                    if matched_poi and matched_poi.location:
                        attr["location"] = {
                            "longitude": matched_poi.location.longitude,
                            "latitude": matched_poi.location.latitude
                        }
                        self.logger.debug(f"从POI匹配到坐标: "
                              f"({matched_poi.location.longitude}, {matched_poi.location.latitude})")
                    else:
                        self.logger.warning(f"未找到匹配POI，使用默认坐标")
                        attr["location"] = {"longitude": 116.4, "latitude": 39.9}
                else:
                    # 验证坐标是否有效
                    loc = attr["location"]
                    lng = loc.get("longitude") or loc.get("lng")
                    lat = loc.get("latitude") or loc.get("lat")
                    if not lng or not lat or (lng == 0 and lat == 0):
                        self.logger.warning(f"坐标无效，尝试从POI匹配...")
                        matched_poi = poi_index.get(attr_name.lower())
                        if matched_poi and matched_poi.location:
                            attr["location"] = {
                                "longitude": matched_poi.location.longitude,
                                "latitude": matched_poi.location.latitude
                            }
                    else:
                        self.logger.debug(f"坐标有效: ({lng}, {lat})")

        return data

    def _create_default_days(
        self,
        request: TripRequest,
        pois: List[POI]
    ) -> List[Dict[str, Any]]:
        """创建默认行程"""
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        days = []

        attractions_per_day = 3
        poi_index = 0

        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)

            day_attractions = []
            for j in range(attractions_per_day):
                if poi_index < len(pois):
                    poi = pois[poi_index]
                    day_attractions.append({
                        "name": poi.name,
                        "address": poi.address,
                        "location": {
                            "longitude": poi.location.longitude,
                            "latitude": poi.location.latitude
                        },
                        "visit_duration": 120,
                        "description": f"{request.city}推荐景点",
                        "category": poi.category or "景点",
                        "ticket_price": 50
                    })
                    poi_index += 1
                else:
                    day_attractions.append({
                        "name": f"{request.city}景点{i*3+j+1}",
                        "address": f"{request.city}市中心",
                        "location": {"longitude": 116.4, "latitude": 39.9},
                        "visit_duration": 120,
                        "description": "推荐景点",
                        "category": "景点",
                        "ticket_price": 50
                    })

            days.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_index": i,
                "description": f"第{i+1}天 - {request.city}游览",
                "transportation": request.transportation,
                "accommodation": request.accommodation,
                "attractions": day_attractions,
                "meals": [
                    {"type": "breakfast", "name": "早餐", "description": "当地特色早餐", "estimated_cost": 30},
                    {"type": "lunch", "name": "午餐", "description": "当地特色午餐", "estimated_cost": 50},
                    {"type": "dinner", "name": "晚餐", "description": "当地特色晚餐", "estimated_cost": 80}
                ]
            })

        return days

    def _create_fallback_plan(
        self,
        request: TripRequest,
        pois: List[POI],
        hotels: List[Hotel],
        weather: List[Weather]
    ) -> Dict[str, Any]:
        """创建fallback计划"""
        return {
            "city": request.city,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "days": self._create_default_days(request, pois),
            "weather_info": [w.model_dump() for w in weather],
            "overall_suggestions": f"这是{request.city}的{request.travel_days}天旅行计划。",
            "budget": {
                "total_attractions": 200,
                "total_hotels": 900,
                "total_meals": 480,
                "total_transportation": 100,
                "total": 1680
            }
        }


# 单例实例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service