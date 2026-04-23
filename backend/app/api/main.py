"""FastAPI 主应用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ..core.config import get_settings
from ..core.llm import setup_langsmith  # 显式导入以确保LangSmith设置
from .routes import trip, chat, map, config

# 启动时设置 LangSmith
setup_langsmith()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    # 启动时
    print("\n" + "=" * 60)
    print(f"[START] {settings.app_name} v{settings.app_version}")
    print("=" * 60)
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"DeepSeek API Key: {'已配置' if settings.deepseek_api_key else '未配置'}")
    print(f"阿里云 API Key: {'已配置' if settings.aliyun_dashscope_api_key else '未配置'}")
    print(f"高德地图 API Key: {'已配置' if settings.amap_api_key else '未配置'}")
    print(f"LangSmith 追踪: {'已启用' if settings.langchain_tracing_v2 else '未启用'}")
    if settings.langchain_tracing_v2:
        print(f"LangSmith 项目: {settings.langchain_project}")
    print(f"CORS Origins: {settings.get_cors_origins_list()}")
    print("=" * 60 + "\n")

    yield

    # 关闭时
    print("\n[STOP] 应用正在关闭...\n")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## LangGraph 智能旅行助手

基于 LangGraph 和 LangChain 构建的多 Agent 协作旅行规划系统。

### 核心特性
- 多 Agent 协作：POI搜索、天气查询、酒店推荐、行程规划
- Human-in-the-loop：关键决策点用户确认
- 多轮对话：支持追问和行程调整
- Agent 可观测性：集成 LangSmith
- 记忆系统：保存用户偏好
- 向量检索：景点知识库

### Agent 流程
```
POI搜索 -> 天气查询 -> 酒店推荐 -> 行程规划 -> 用户审核
```
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS 配置 - 允许所有来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(trip.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(map.router, prefix="/api")
    app.include_router(config.router, prefix="/api")

    # 根路由
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs"
        }

    # 健康检查
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()
