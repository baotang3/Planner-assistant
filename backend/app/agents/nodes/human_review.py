"""Human-in-the-loop 节点 - 用户审核"""

from typing import Dict, Any
from datetime import datetime

from ...models.schemas import AgentState, AgentStep, NodeType, TripStatus


async def human_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    人工审核节点

    此节点会暂停执行，等待用户审核和反馈

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    agent_state = AgentState(**state)

    step = AgentStep(
        node=NodeType.HUMAN_REVIEW.value,
        status="waiting",
        input={"itinerary": agent_state.itinerary.model_dump() if agent_state.itinerary else None}
    )

    agent_state.steps.append(step)
    agent_state.current_node = NodeType.HUMAN_REVIEW.value
    agent_state.status = TripStatus.NEED_CONFIRM
    agent_state.need_human_review = True
    agent_state.updated_at = datetime.now()

    return agent_state.model_dump()


async def process_feedback(state: Dict[str, Any], action: str, modifications: dict = None) -> Dict[str, Any]:
    """
    处理用户反馈

    Args:
        state: 当前状态
        action: 用户动作 (approve/modify/reject)
        modifications: 修改内容

    Returns:
        更新后的状态
    """
    agent_state = AgentState(**state)

    if action == "approve":
        agent_state.status = TripStatus.COMPLETED
        agent_state.need_human_review = False
        agent_state.human_feedback = "approved"

    elif action == "modify" and modifications:
        # 应用修改
        if agent_state.itinerary:
            # 更新行程
            for key, value in modifications.items():
                if hasattr(agent_state.itinerary, key):
                    setattr(agent_state.itinerary, key, value)
            agent_state.human_feedback = f"modified: {modifications}"

    elif action == "reject":
        agent_state.status = TripStatus.FAILED
        agent_state.need_human_review = False
        agent_state.human_feedback = "rejected"

    agent_state.updated_at = datetime.now()
    return agent_state.model_dump()
