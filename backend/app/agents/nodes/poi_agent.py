"""POI 搜索 Agent 节点"""

from typing import Dict, Any
from datetime import datetime

from ...services.amap_service import get_amap_service
from ...models.schemas import AgentState, AgentStep, NodeType, TripStatus


async def poi_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    POI 搜索节点

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    agent_state = AgentState(**state)

    step = AgentStep(
        node=NodeType.POI_SEARCH.value,
        status="running",
        input={
            "city": agent_state.city,
            "preferences": agent_state.preferences
        }
    )

    try:
        # 1. 根据偏好确定搜索关键词
        search_keywords = agent_state.preferences if agent_state.preferences else ["景点"]

        # 如果没有偏好，使用默认关键词
        if not search_keywords:
            search_keywords = ["景点", "旅游"]

        # 2. 调用高德地图 API 搜索 POI（并行搜索多个关键词）
        amap = get_amap_service()
        all_pois = []

        # 并行搜索多个关键词以提高性能
        import asyncio
        tasks = [
            amap.search_poi(keyword, agent_state.city, citylimit=True)
            for keyword in search_keywords[:3]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_pois.extend(result)

        # 去重
        seen = set()
        unique_pois = []
        for poi in all_pois:
            if poi.name not in seen:
                seen.add(poi.name)
                unique_pois.append(poi)

        # 更新状态
        step.status = "completed"
        step.output = {
            "pois_count": len(unique_pois),
            "keywords_used": search_keywords
        }

        agent_state.pois = unique_pois[:20]
        agent_state.steps.append(step)
        agent_state.current_node = NodeType.POI_SEARCH.value
        agent_state.updated_at = datetime.now()

        return agent_state.model_dump()

    except Exception as e:
        step.status = "failed"
        step.error = str(e)
        agent_state.errors.append(f"POI搜索失败: {str(e)}")
        agent_state.steps.append(step)
        return agent_state.model_dump()
