"""旅行规划器异常处理模块

定义统一的业务异常类和全局异常处理器。
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class TripPlannerException(HTTPException):
    """旅行规划器业务异常基类"""

    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        error_code: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or self.__class__.__name__
        self.extra_data = extra_data or {}


class POISearchException(TripPlannerException):
    """POI搜索异常"""

    def __init__(
        self,
        detail: str = "POI搜索失败",
        keyword: Optional[str] = None,
        city: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        data = extra_data or {}
        if keyword:
            data["keyword"] = keyword
        if city:
            data["city"] = city

        super().__init__(
            detail=detail,
            status_code=400,
            error_code="POI_SEARCH_ERROR",
            extra_data=data
        )


class HotelSearchException(TripPlannerException):
    """酒店搜索异常"""

    def __init__(
        self,
        detail: str = "酒店搜索失败",
        city: Optional[str] = None,
        hotel_type: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        data = extra_data or {}
        if city:
            data["city"] = city
        if hotel_type:
            data["hotel_type"] = hotel_type

        super().__init__(
            detail=detail,
            status_code=400,
            error_code="HOTEL_SEARCH_ERROR",
            extra_data=data
        )


class WeatherQueryException(TripPlannerException):
    """天气查询异常"""

    def __init__(
        self,
        detail: str = "天气查询失败",
        city: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        data = extra_data or {}
        if city:
            data["city"] = city

        super().__init__(
            detail=detail,
            status_code=400,
            error_code="WEATHER_QUERY_ERROR",
            extra_data=data
        )


class LLMServiceException(TripPlannerException):
    """LLM服务异常"""

    def __init__(
        self,
        detail: str = "LLM服务调用失败",
        provider: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        data = extra_data or {}
        if provider:
            data["provider"] = provider

        super().__init__(
            detail=detail,
            status_code=500,
            error_code="LLM_SERVICE_ERROR",
            extra_data=data
        )


class ValidationException(TripPlannerException):
    """数据验证异常"""

    def __init__(
        self,
        detail: str = "数据验证失败",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        data = extra_data or {}
        if field:
            data["field"] = field
        if value is not None:
            data["value"] = value

        super().__init__(
            detail=detail,
            status_code=400,
            error_code="VALIDATION_ERROR",
            extra_data=data
        )


async def trip_planner_exception_handler(request: Request, exc: TripPlannerException) -> JSONResponse:
    """全局异常处理器"""
    response_data = {
        "success": False,
        "error": {
            "code": exc.error_code,
            "message": exc.detail,
            "type": exc.__class__.__name__,
            **exc.extra_data
        }
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    response_data = {
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "type": exc.__class__.__name__,
            "detail": str(exc)
        }
    }

    return JSONResponse(
        status_code=500,
        content=response_data
    )