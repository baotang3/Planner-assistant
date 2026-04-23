# Planner-assistant

LangGraph智能旅行助手 - 基于 LangGraph 和 LangChain 构建的智能旅行行程规划系统，支持多 Agent 协作、流式响应、预算控制和地图可视化。

ps:本项目为hello-agents在langgraph上借助claude code的重构，目前所有流程均可以跑通，后续还会完善新的功能，欢迎大家提出宝贵的意见和建议，一起学习一起进大厂！！！

## 功能特性

### 核心功能

- **智能行程规划**: 根据目的地、日期、偏好自动生成详细行程
- **预算控制**: 支持设置预算范围，AI 会根据预算合理安排景点、餐饮和住宿
- **实时进度反馈**: SSE 流式响应，实时展示 Agent 执行进度
- **地图可视化**: 高德地图集成，展示景点位置和路线
- **多轮对话**: 支持自然语言交互，逐步完善行程需求
- **行程持久化**: 每次规划结果自动保存为 JSON 文件

### 技术亮点

- **多 LLM 支持**: DeepSeek、阿里云百炼，可灵活切换
- **高德地图 API**: POI 搜索、天气查询、酒店推荐、地理编码
- **类型安全**: 后端 Pydantic + 前端 TypeScript 全栈类型校验
- **响应式 UI**: Vue 3 + Element Plus，支持移动端

## 项目结构

```
langgraph-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── routes/
│   │   │   │   ├── trip.py    # 行程规划接口
│   │   │   │   ├── chat.py    # 多轮对话接口
│   │   │   │   └── map.py     # 地图服务接口
│   │   │   └── main.py        # FastAPI 入口
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 环境配置
│   │   │   └── llm.py         # LLM 工厂
│   │   ├── models/
│   │   │   └── schemas.py     # 数据模型
│   │   ├── services/
│   │   │   └── amap_service.py # 高德地图服务
│   │   └── saved_results/     # 行程结果存储
│   ├── requirements.txt
│   └── .env                   # 环境变量 (需配置)
│
└── frontend/                   # 前端应用
    ├── src/
    │   ├── views/
    │   │   ├── Home.vue       # 表单模式主页
    │   │   ├── Result.vue     # 结果展示页
    │   │   └── Chat.vue       # 对话模式页
    │   ├── stores/            # Pinia 状态管理
    │   ├── services/          # API 服务
    │   └── types/             # TypeScript 类型
    ├── package.json
    └── .env                   # 环境变量 (需配置)
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Conda (推荐)

### 1. 后端配置

```bash
cd backend

# 创建并激活 Conda 环境
conda create -n agent_planner python=3.10
conda activate agent_planner

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM 配置 (至少配置一个)
DEEPSEEK_API_KEY=your_deepseek_api_key
ALIYUN_DASHSCOPE_API_KEY=your_aliyun_api_key

# 高德地图 API (必需)
AMAP_API_KEY=your_amap_web_api_key

# LangSmith 追踪 (可选)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=trip-planner-agent
```

启动后端服务：

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_AMAP_KEY=your_amap_js_api_key
```

> 注意：高德地图需要分别申请 Web API Key (后端) 和 JS API Key (前端)

启动前端服务：

```bash
npm run dev
```

访问 http://localhost:5173 开始使用。

## API 接口

### 行程规划 (同步)

```http
POST /api/trip/plan
Content-Type: application/json

{
  "city": "武汉",
  "start_date": "2026-04-23",
  "end_date": "2026-04-24",
  "travel_days": 2,
  "transportation": "公共交通",
  "accommodation": "舒适型酒店",
  "preferences": ["历史文化"],
  "free_text_input": "想看黄鹤楼",
  "budget": [1000, 3000],
  "llm_provider": "deepseek"
}
```

### 行程规划 (流式)

```http
POST /api/trip/plan/stream
Content-Type: application/json

# 返回 SSE 流式事件
data: {"node": "init", "status": "running", "message": "正在初始化..."}
data: {"node": "poi_search", "status": "completed", "message": "找到 20 个景点"}
data: {"node": "complete", "data": {"itinerary": {...}}}
```

### 多轮对话

```http
POST /api/chat/message
Content-Type: application/json

{
  "session_id": "session_xxx",
  "message": "我想去武汉玩两天，预算两千左右",
  "llm_provider": "deepseek"
}
```

## 使用说明

### 表单模式

1. 输入目的地城市、出发和返回日期
2. 选择交通方式和住宿偏好
3. 勾选旅行偏好 (历史文化、自然风光、美食等)
4. 设置预算范围 (滑动条调整)
5. 选择 AI 模型
6. 点击"开始规划行程"
7. 实时查看 Agent 执行进度
8. 规划完成后自动跳转结果页

### 对话模式

支持自然语言交互，例如：
- "我想去北京玩三天"
- "预算大概两千块"
- "喜欢历史文化景点"
- "帮我推荐一些美食"

### 结果展示

- 行程概览：城市、日期、天数
- 地图展示：景点位置标记
- 每日行程：景点详情、游玩时长、门票价格
- 餐饮推荐：早餐、午餐、晚餐
- 住宿安排：酒店信息、价格范围
- 预算估算：分类费用统计
- PDF 导出：保存行程计划

## 数据存储

每次行程规划完成后，结果会自动保存到 `backend/app/saved_results/` 目录：

```json
{
  "session_id": "xxx",
  "created_at": "2026-04-22T15:00:00",
  "request": {
    "city": "武汉",
    "budget": [1000, 3000],
    ...
  },
  "result": {
    "city": "武汉",
    "days": [...],
    "budget": {...}
  }
}
```

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI | Web 框架 |
| LangChain | LLM 应用框架 |
| Pydantic | 数据验证 |
| httpx | 异步 HTTP 客户端 |
| uvicorn | ASGI 服务器 |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 | 前端框架 |
| TypeScript | 类型安全 |
| Element Plus | UI 组件库 |
| Pinia | 状态管理 |
| Axios | HTTP 客户端 |
| Vue Router | 路由管理 |

### 外部服务

| 服务 | 用途 |
|------|------|
| 高德地图 API | POI 搜索、天气、地理编码 |
| DeepSeek | LLM 服务 |
| 阿里云百炼 | LLM 服务 (通义千问) |

## 注意事项

1. **API Key 安全**: 请勿将 `.env` 文件提交到版本控制
2. **高德地图 Key**: 需要分别申请 Web 服务 API Key (后端) 和 JS API Key (前端)
3. **LLM 费用**: 使用 DeepSeek 或阿里云百炼会产生 API 调用费用
4. **预算控制**: AI 生成的预算为估算值，实际花费可能有所不同

## 开发计划

- [ ] 添加更多 LLM 提供商 (OpenAI, Claude)
- [ ] 支持行程分享功能
- [ ] 添加用户收藏和历史记录
- [ ] 优化移动端体验
- [ ] 添加景点评价和图片
