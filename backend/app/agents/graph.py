"""LangGraph 主图定义 - 多 Agent 协作流程"""

from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage

from ..models.schemas import AgentState, NodeType, TripStatus
from .nodes.poi_agent import poi_search_node
from .nodes.weather_agent import weather_node
from .nodes.hotel_agent import hotel_node
from .nodes.planner_agent import planner_node
from .nodes.human_review import human_review_node


# 定义状态类型
class GraphState(TypedDict):
    """图状态"""
    session_id: str
    city: str
    start_date: str
    end_date: str
    travel_days: int
    transportation: str
    accommodation: str
    preferences: list
    free_text_input: str
    pois: list
    weather: list
    hotels: list
    itinerary: dict
    current_node: str
    status: str
    steps: list
    errors: list
    need_human_review: bool
    human_feedback: str
    llm_provider: str


def router_node(state: GraphState) -> Literal["poi_search", "weather", "hotel", "planner"]:
    """
    路由节点 - 决定执行顺序

    根据当前状态决定下一步执行哪个节点
    """
    # 检查哪些数据已经获取
    has_pois = bool(state.get("pois"))
    has_weather = bool(state.get("weather"))
    has_hotels = bool(state.get("hotels"))

    # 执行顺序: POI -> (Weather + Hotel 并行) -> Planner
    if not has_pois:
        return "poi_search"
    elif not has_weather:
        return "weather"
    elif not has_hotels:
        return "hotel"
    else:
        return "planner"


def should_continue(state: GraphState) -> Literal["continue", "human_review", "end"]:
    """
    判断是否继续执行

    Returns:
        continue: 继续执行下一个节点
        human_review: 进入人工审核
        end: 结束
    """
    status = state.get("status", "")

    if status == TripStatus.FAILED.value:
        return "end"

    if state.get("need_human_review"):
        return "human_review"

    if state.get("itinerary"):
        return "human_review"

    return "continue"


def create_trip_planner_graph():
    """
    创建旅行规划图

    图结构:
    START -> poi_search -> weather -> hotel -> planner -> human_review -> END
              |              |          |            |
              v              v          v            v
           (router)      (router)   (router)    (should_continue)
    """
    # 创建图
    workflow = StateGraph(GraphState)

    # 添加节点
    workflow.add_node("poi_search", poi_search_node)
    workflow.add_node("weather", weather_node)
    workflow.add_node("hotel", hotel_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("human_review", human_review_node)

    # 设置入口
    workflow.set_entry_point("poi_search")

    # 添加边 - 线性流程
    workflow.add_edge("poi_search", "weather")
    workflow.add_edge("weather", "hotel")
    workflow.add_edge("hotel", "planner")

    # 条件边 - planner 后判断是否需要人工审核
    workflow.add_conditional_edges(
        "planner",
        should_continue,
        {
            "human_review": "human_review",
            "end": END
        }
    )

    # human_review 后结束
    workflow.add_edge("human_review", END)

    # 编译图，添加 checkpointer 用于持久化
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


# 全局图实例
_graph_instance = None


def get_graph():
    """获取图实例"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_trip_planner_graph()
    return _graph_instance
