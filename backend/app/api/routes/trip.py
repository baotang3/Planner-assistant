"""旅行规划 API 路由"""

import uuid
import json
import traceback
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse

from ...models.schemas import (
    TripRequest, TripPlanResponse, StreamingResponse,
    UserFeedback, TripStatus, TripPlan, DayPlan, Attraction, Meal, Location, Hotel, Budget
)
from ...services.trip_coordinator import get_trip_coordinator

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 保存结果的目录
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saved_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _save_trip_result(session_id: str, trip_plan: dict, request: TripRequest):
    """保存行程规划结果到JSON文件"""
    try:
        # 构建保存数据
        save_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "request": {
                "city": request.city,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "travel_days": request.travel_days,
                "transportation": request.transportation,
                "accommodation": request.accommodation,
                "preferences": request.preferences,
                "free_text_input": request.free_text_input,
                "budget": request.budget
            },
            "result": trip_plan
        }

        # 生成文件名：城市_日期_session_id.json
        filename = f"{request.city}_{request.start_date}_{session_id[:8]}.json"
        filepath = os.path.join(RESULTS_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"[Trip Plan] 结果已保存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"[Trip Plan] 保存结果失败: {e}")
        return None


@router.post("/plan")
async def create_trip_plan(request: TripRequest):
    """
    创建旅行计划 - 同步接口
    """
    session_id = request.session_id or str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"[Trip Plan] 开始处理请求")
    print(f"[Trip Plan] Session ID: {session_id}")
    print(f"[Trip Plan] 城市: {request.city}")
    print(f"[Trip Plan] 日期: {request.start_date} ~ {request.end_date}")
    print(f"[Trip Plan] 天数: {request.travel_days}")
    print(f"[Trip Plan] LLM Provider: {request.llm_provider}")
    print(f"{'='*60}\n")

    try:
        # 使用行程规划协调器
        coordinator = get_trip_coordinator()

        # 生成行程计划
        trip_plan = await coordinator.plan_trip_sync(request)

        # 保存结果到文件
        _save_trip_result(session_id, trip_plan, request)

        return {
            "success": True,
            "message": "旅行计划生成成功",
            "data": trip_plan,
            "status": "completed",
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Trip Plan] 发生错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")




@router.post("/plan/stream")
async def create_trip_plan_stream(request: TripRequest):
    """创建旅行计划 - 流式响应"""
    session_id = request.session_id or str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"[Trip Plan Stream] 开始处理请求")
    print(f"[Trip Plan Stream] Session ID: {session_id}")
    print(f"[Trip Plan Stream] 城市: {request.city}")
    print(f"{'='*60}\n")

    async def event_generator():
        try:
            # Step 1: 初始化
            yield _create_sse_event(session_id, 1, "init", "running", "正在初始化...")

            # 使用行程规划协调器（流式模式）
            coordinator = get_trip_coordinator()

            # 定义进度回调函数
            def progress_callback(step, node, status, message, data=None):
                # 将进度转换为SSE事件
                nonlocal session_id
                yield _create_sse_event(session_id, step, node, status, message, data or {})

            # 由于回调函数是生成器，我们需要特殊处理
            # 创建一个队列来收集进度事件
            import asyncio
            progress_queue = asyncio.Queue()

            def progress_handler(step, node, status, message, data=None):
                # 将进度事件放入队列
                event = _create_sse_event(session_id, step, node, status, message, data or {})
                asyncio.create_task(progress_queue.put(event))

            # 启动行程规划任务
            import asyncio
            planning_task = asyncio.create_task(
                coordinator.plan_trip_stream(request, progress_handler)
            )

            # 处理进度事件
            while True:
                try:
                    # 等待进度事件或规划任务完成
                    done, pending = await asyncio.wait(
                        [asyncio.create_task(progress_queue.get()), planning_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in done:
                        if task == planning_task:
                            # 规划任务完成
                            try:
                                trip_plan = task.result()

                                # 发送完成事件
                                yield _create_sse_event(session_id, 6, "complete", "completed",
                                                        "行程规划已生成，正在跳转...",
                                                        {"itinerary": trip_plan})

                                # 保存结果到文件
                                _save_trip_result(session_id, trip_plan, request)

                                print(f"[Trip Plan Stream] 完成，共 {len(trip_plan.get('days', []))} 天行程")
                                return
                            except Exception as e:
                                yield _create_sse_event(session_id, 0, "error", "failed",
                                                        f"执行失败: {str(e)}")
                                return
                        else:
                            # 进度事件
                            event = task.result()
                            yield event

                            # 继续处理下一个事件
                            progress_queue.task_done()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    yield _create_sse_event(session_id, 0, "error", "failed",
                                            f"进度处理失败: {str(e)}")
                    break

        except Exception as e:
            traceback.print_exc()
            yield _create_sse_event(session_id, 0, "error", "failed",
                                    f"执行失败: {str(e)}")

    return FastAPIStreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def _create_sse_event(session_id: str, step: int, node: str, status: str,
                       message: str, data: dict = None) -> str:
    """创建 SSE 事件"""
    event = {
        "session_id": session_id,
        "step": step,
        "node": node,
        "status": status,
        "message": message,
        "data": data or {}
    }
    return f"data: {json.dumps(event)}\n\n"












@router.post("/feedback")
async def submit_feedback(feedback: UserFeedback):
    """提交用户反馈"""
    return {
        "success": True,
        "message": f"反馈已处理: {feedback.action}",
        "status": "completed"
    }


@router.get("/status/{session_id}")
async def get_trip_status(session_id: str):
    """获取旅行计划状态"""
    return {
        "session_id": session_id,
        "status": "completed",
        "current_node": "",
        "steps": [],
        "errors": [],
        "need_human_review": False
    }


@router.get("/result/{session_id}")
async def get_trip_result(session_id: str):
    """获取旅行计划结果"""
    return {
        "success": True,
        "message": "获取成功",
        "data": None,
        "status": "pending"
    }