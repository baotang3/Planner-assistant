"""多轮对话 API 路由"""

import uuid
import traceback
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from ...models.schemas import ChatMessage, ChatResponse, TripPlan
from ...core.llm import get_llm, invoke_llm_with_logging
from ...core.memory import get_memory_manager
from ...services.amap_service import get_amap_service

router = APIRouter(prefix="/chat", tags=["多轮对话"])


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatMessage):
    """发送聊天消息 - 支持多轮对话和实时数据查询"""
    session_id = request.session_id or str(uuid.uuid4())
    llm_provider = request.llm_provider or "deepseek"

    print(f"\n{'='*60}")
    print(f"[Chat] 收到消息: {request.message}")
    print(f"[Chat] Session ID: {session_id}")
    print(f"[Chat] LLM Provider: {llm_provider}")
    print(f"{'='*60}")

    memory_manager = get_memory_manager()
    memory = memory_manager.get_memory(session_id)

    # 添加用户消息到记忆
    memory.add_user_message(request.message)

    try:
        llm = get_llm(llm_provider)

        # 分析用户意图并获取相关信息
        user_message = request.message.lower()

        # 检查是否询问天气
        if "天气" in user_message or "气温" in user_message or "下雨" in user_message:
            print("[Chat] 检测到天气查询意图")
            response_text = await _handle_weather_query(llm, request.message, memory, llm_provider)

        # 检查是否询问酒店 (必须在景点之前检查，因为"推荐"关键词重叠)
        elif "酒店" in user_message or "住宿" in user_message or "住哪" in user_message:
            print("[Chat] 检测到酒店查询意图")
            response_text = await _handle_hotel_query(llm, request.message, memory, llm_provider)

        # 检查是否询问景点
        elif "景点" in user_message or "好玩" in user_message or "去哪" in user_message:
            print("[Chat] 检测到景点查询意图")
            response_text = await _handle_poi_query(llm, request.message, memory, llm_provider)

        # 检查是否规划行程
        elif "规划" in user_message or "行程" in user_message or "安排" in user_message:
            print("[Chat] 检测到行程规划意图")
            response_text = await _handle_trip_planning(llm, request.message, memory)

        # 通用对话
        else:
            print("[Chat] 通用对话")
            response_text = await _general_chat(llm, request.message, memory.get_history_str(), llm_provider)

        # 添加 AI 消息到记忆
        memory.add_ai_message(response_text)

        print(f"\n{'='*60}")
        print(f"[Chat] 最终响应: {response_text[:200]}...")
        print(f"{'='*60}\n")

        return ChatResponse(
            session_id=session_id,
            response=response_text,
            trip_plan=None
        )

    except Exception as e:
        print(f"[Chat] 错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


async def _handle_weather_query(llm, message: str, memory, llm_provider: str = "deepseek") -> str:
    """处理天气查询"""
    print(f"\n{'='*60}")
    print("[Chat] _handle_weather_query 开始")
    print(f"{'='*60}")

    # 从消息中提取城市名
    city = _extract_city_from_message(message)
    print(f"[Chat] 提取的城市: {city}")

    # 保存城市偏好
    if city:
        memory.set_preference("city", city)

    if not city:
        return "请问您想查询哪个城市的天气呢？"

    try:
        # 调用高德地图API获取真实天气数据
        print(f"[Chat] 调用高德地图API获取 {city} 的天气")
        amap = get_amap_service()
        weather_data = await amap.get_weather(city)

        print(f"[Chat] 获取到 {len(weather_data)} 天天气数据")

        if not weather_data:
            return f"抱歉，暂时无法获取 {city} 的天气信息，请稍后再试。"

        # 格式化天气数据
        weather_info = []
        for w in weather_data[:4]:  # 最多显示4天
            info = f"{w.date}: {w.day_weather} {w.day_temp}C / {w.night_weather} {w.night_temp}C, {w.wind_direction}风 {w.wind_power}级"
            weather_info.append(info)

        weather_str = "\n".join(weather_info)
        print(f"[Chat] 格式化后的天气信息:\n{weather_str}")

        # 让LLM组织回复
        prompt = f"""用户询问: {message}

以下是{city}的真实天气数据:
{weather_str}

请用友好的方式向用户介绍天气情况，并给出旅行建议。回复要简洁，不超过200字。"""

        # 使用带日志的LLM调用
        response_content = await invoke_llm_with_logging(llm, prompt, llm_provider)

        print(f"[Chat] 天气查询完成")
        print(f"{'='*60}\n")
        return response_content

    except Exception as e:
        print(f"[Chat] 天气查询失败: {e}")
        traceback.print_exc()
        return f"抱歉，查询{city}天气时出现错误: {str(e)}"


async def _handle_poi_query(llm, message: str, memory, llm_provider: str = "deepseek") -> str:
    """处理景点查询"""
    print(f"\n{'='*60}")
    print("[Chat] _handle_poi_query 开始")
    print(f"{'='*60}")

    city = _extract_city_from_message(message)
    city = city or memory.get_preference("city", "")

    print(f"[Chat] 城市: {city}")

    if not city:
        return "请问您想了解哪个城市的景点呢？"

    # 保存城市偏好
    memory.set_preference("city", city)

    try:
        # 调用高德地图API获取景点数据
        print(f"[Chat] 调用高德地图API获取 {city} 的景点")
        amap = get_amap_service()

        # 搜索多种类型的景点
        all_pois = []
        keywords = ["景点", "公园", "博物馆", "名胜古迹"]

        for keyword in keywords[:2]:  # 只搜索2种类型
            try:
                pois = await amap.search_poi(keyword, city, citylimit=True)
                print(f"[Chat] 搜索 '{keyword}' 找到 {len(pois)} 个结果")
                all_pois.extend(pois)
            except Exception as e:
                print(f"[Chat] 搜索 '{keyword}' 失败: {e}")

        # 去重
        seen = set()
        unique_pois = []
        for poi in all_pois:
            if poi.name not in seen:
                seen.add(poi.name)
                unique_pois.append(poi)

        print(f"[Chat] 去重后共 {len(unique_pois)} 个景点")

        if not unique_pois:
            return f"抱歉，暂时没有找到{city}的景点信息。"

        # 格式化景点数据
        poi_list = []
        for poi in unique_pois[:8]:  # 最多显示8个
            info = f"- {poi.name}"
            if poi.rating:
                info += f" (评分: {poi.rating})"
            if poi.address:
                info += f", 地址: {poi.address}"
            poi_list.append(info)

        poi_str = "\n".join(poi_list)
        print(f"[Chat] 格式化后的景点信息:\n{poi_str}")

        # 让LLM组织回复
        prompt = f"""用户询问: {message}

以下是{city}的真实景点数据:
{poi_str}

请用友好的方式向用户介绍这些景点，并给出游玩建议。回复要简洁，不超过300字。"""

        # 使用带日志的LLM调用
        response_content = await invoke_llm_with_logging(llm, prompt, llm_provider)

        print(f"[Chat] 景点查询完成")
        print(f"{'='*60}\n")
        return response_content

    except Exception as e:
        print(f"[Chat] 景点查询失败: {e}")
        traceback.print_exc()
        return f"抱歉，查询{city}景点时出现错误: {str(e)}"


async def _handle_hotel_query(llm, message: str, memory, llm_provider: str = "deepseek") -> str:
    """处理酒店查询"""
    print(f"\n{'='*60}")
    print("[Chat] _handle_hotel_query 开始")
    print(f"{'='*60}")

    city = _extract_city_from_message(message)
    city = city or memory.get_preference("city", "")

    print(f"[Chat] 城市: {city}")

    if not city:
        return "请问您想了解哪个城市的酒店呢？"

    memory.set_preference("city", city)

    try:
        print(f"[Chat] 调用高德地图API获取 {city} 的酒店")
        amap = get_amap_service()
        hotels = await amap.search_hotels(city, "酒店")

        print(f"[Chat] 找到 {len(hotels)} 家酒店")

        if not hotels:
            return f"抱歉，暂时没有找到{city}的酒店信息。"

        # 格式化酒店数据
        hotel_list = []
        for hotel in hotels[:6]:
            info = f"- {hotel.name}"
            if hotel.rating:
                info += f" (评分: {hotel.rating})"
            if hotel.address:
                info += f", 地址: {hotel.address}"
            hotel_list.append(info)

        hotel_str = "\n".join(hotel_list)
        print(f"[Chat] 格式化后的酒店信息:\n{hotel_str}")

        prompt = f"""用户询问: {message}

以下是{city}的真实酒店数据:
{hotel_str}

请用友好的方式向用户介绍这些酒店。回复要简洁，不超过200字。"""

        # 使用带日志的LLM调用
        response_content = await invoke_llm_with_logging(llm, prompt, llm_provider)

        print(f"[Chat] 酒店查询完成")
        print(f"{'='*60}\n")
        return response_content

    except Exception as e:
        print(f"[Chat] 酒店查询失败: {e}")
        traceback.print_exc()
        return f"抱歉，查询{city}酒店时出现错误: {str(e)}"


async def _handle_trip_planning(llm, message: str, memory) -> str:
    """处理行程规划请求"""
    print("[Chat] _handle_trip_planning 开始")

    city = _extract_city_from_message(message)
    if city:
        memory.set_preference("city", city)

    return "好的，我来帮您规划行程！请切换到表单模式（点击左侧\"切换到表单模式\"），填写详细信息后开始规划。您也可以直接告诉我：目的地城市、出发日期、返回日期，我来帮您规划。"


async def _general_chat(llm, message: str, history: str, llm_provider: str = "deepseek") -> str:
    """通用对话"""
    print(f"\n{'='*60}")
    print("[Chat] _general_chat 开始")
    print(f"{'='*60}")

    history_str = history[-1000:] if history else "无"

    prompt = f"""你是一个友好的旅行助手，可以帮助用户查询天气、景点、酒店等信息。

对话历史:
{history_str}

用户消息: {message}

请友好地回复用户。如果用户询问天气、景点、酒店等，告诉他们我可以帮忙查询。回复要简洁，不超过150字。"""

    # 使用带日志的LLM调用
    response_content = await invoke_llm_with_logging(llm, prompt, llm_provider)

    print(f"[Chat] 通用对话完成")
    print(f"{'='*60}\n")
    return response_content


def _extract_city_from_message(message: str) -> str:
    """从消息中提取城市名"""
    import re

    # 常见城市列表
    cities = [
        "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "成都",
        "重庆", "武汉", "西安", "厦门", "青岛", "大连", "天津", "长沙",
        "郑州", "济南", "福州", "昆明", "贵阳", "南宁", "海口", "三亚",
        "拉萨", "乌鲁木齐", "哈尔滨", "沈阳", "长春", "石家庄", "太原",
        "呼和浩特", "兰州", "银川", "西宁", "南昌", "合肥", "无锡", "宁波"
    ]

    message_lower = message.lower()

    for city in cities:
        if city in message:
            print(f"[Chat] 从消息中提取到城市: {city}")
            return city

    # 尝试匹配 "XX市" 或 "XX的"
    match = re.search(r'([^\s，。！？]{2,4})(?:市|的|天气|景点|酒店)', message)
    if match:
        city = match.group(1)
        print(f"[Chat] 通过正则提取到城市: {city}")
        return city

    return ""


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """获取对话历史"""
    memory_manager = get_memory_manager()
    memory = memory_manager.get_memory(session_id)

    return {
        "session_id": session_id,
        "history": [
            {
                "role": "user" if msg.__class__.__name__ == "HumanMessage" else "assistant",
                "content": msg.content
            }
            for msg in memory.get_history()
        ]
    }


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """清空对话历史"""
    memory_manager = get_memory_manager()
    memory_manager.clear_memory(session_id)

    return {"success": True, "message": "对话历史已清空"}