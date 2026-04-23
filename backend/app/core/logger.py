"""旅行规划器结构化日志模块

提供统一的日志记录接口，支持不同日志级别和结构化输出。
"""

import logging
import sys
from typing import Optional, Dict, Any
from .config import get_settings

# 全局日志记录器实例
_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str = "trip_planner") -> logging.Logger:
    """获取或创建日志记录器实例"""
    if name in _loggers:
        return _loggers[name]

    # 创建日志记录器
    logger = logging.getLogger(name)

    # 设置日志级别
    settings = get_settings()
    if settings.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)

        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        # 添加处理器
        logger.addHandler(console_handler)

    # 避免日志传播到根日志记录器
    logger.propagate = False

    _loggers[name] = logger
    return logger


class ServiceLogger:
    """服务专用日志记录器包装类"""

    def __init__(self, service_name: str):
        self.logger = get_logger(f"trip_planner.{service_name}")
        self.service_name = service_name

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self.logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs):
        """记录错误信息"""
        self.logger.error(self._format_message(message, **kwargs))

    def exception(self, message: str, exc: Exception, **kwargs):
        """记录异常信息"""
        self.logger.error(self._format_message(f"{message}: {exc}", **kwargs))

    def _format_message(self, message: str, **kwargs) -> str:
        """格式化日志消息"""
        if kwargs:
            extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"[{self.service_name}] {message} | {extra_info}"
        return f"[{self.service_name}] {message}"


# 预定义的服务日志记录器
def get_poi_service_logger() -> ServiceLogger:
    """获取POI服务日志记录器"""
    return ServiceLogger("poi_service")


def get_hotel_service_logger() -> ServiceLogger:
    """获取酒店服务日志记录器"""
    return ServiceLogger("hotel_service")


def get_weather_service_logger() -> ServiceLogger:
    """获取天气服务日志记录器"""
    return ServiceLogger("weather_service")


def get_llm_service_logger() -> ServiceLogger:
    """获取LLM服务日志记录器"""
    return ServiceLogger("llm_service")


def get_trip_coordinator_logger() -> ServiceLogger:
    """获取行程协调器日志记录器"""
    return ServiceLogger("trip_coordinator")


def get_amap_service_logger() -> ServiceLogger:
    """获取高德地图服务日志记录器"""
    return ServiceLogger("amap_service")


def get_api_logger() -> ServiceLogger:
    """获取API日志记录器"""
    return ServiceLogger("api")