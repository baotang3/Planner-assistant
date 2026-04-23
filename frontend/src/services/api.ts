import axios from 'axios'
import type {
  TripRequest,
  TripPlanResponse,
  StreamingResponse,
  ChatMessage,
  ChatResponse,
  UserFeedback,
  TripPlan
} from '@/types'

// 使用环境变量中的 API 地址，默认值为 http://localhost:8000
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000'

console.log('API_BASE_URL:', API_BASE_URL || '使用代理')

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加调试日志
apiClient.interceptors.request.use(
  (config) => {
    const url = `${config.baseURL || ''}${config.url || ''}`
    console.log('API Request:', config.method?.toUpperCase(), url, config.data)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 添加调试日志
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// ===========================================
// 旅行规划 API
// ===========================================

/**
 * 创建旅行计划（同步）
 */
export async function createTripPlan(request: TripRequest): Promise<any> {
  const response = await apiClient.post('/api/trip/plan', request)
  return response.data
}

/**
 * 创建旅行计划（流式）
 */
export async function createTripPlanStream(
  request: TripRequest,
  onMessage: (data: StreamingResponse) => void,
  onError: (error: Error) => void,
  onComplete: () => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/trip/plan/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)) as StreamingResponse
            onMessage(data)
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    onError(error as Error)
  } finally {
    onComplete()
  }
}

/**
 * 提交用户反馈
 */
export async function submitFeedback(feedback: UserFeedback): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post('/api/trip/feedback', feedback)
  return response.data
}

/**
 * 批准行程计划
 */
export async function approveTripPlan(sessionId: string, comment?: string): Promise<{ success: boolean; message: string }> {
  return submitFeedback({
    session_id: sessionId,
    action: 'approve',
    comment
  })
}

/**
 * 拒绝行程计划
 */
export async function rejectTripPlan(sessionId: string, comment?: string): Promise<{ success: boolean; message: string }> {
  return submitFeedback({
    session_id: sessionId,
    action: 'reject',
    comment
  })
}

/**
 * 获取旅行计划状态
 */
export async function getTripStatus(sessionId: string): Promise<{
  session_id: string
  status: string
  current_node: string
  steps: unknown[]
  errors: string[]
}> {
  const response = await apiClient.get(`/api/trip/status/${sessionId}`)
  return response.data
}

/**
 * 获取旅行计划结果
 */
export async function getTripResult(sessionId: string): Promise<TripPlanResponse> {
  const response = await apiClient.get<TripPlanResponse>(`/api/trip/result/${sessionId}`)
  return response.data
}

// ===========================================
// 多轮对话 API
// ===========================================

/**
 * 发送聊天消息
 */
export async function sendChatMessage(request: ChatMessage): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/api/chat/message', request)
  return response.data
}

/**
 * 获取对话历史
 */
export async function getChatHistory(sessionId: string): Promise<{
  session_id: string
  history: Array<{ role: string; content: string }>
}> {
  const response = await apiClient.get(`/api/chat/history/${sessionId}`)
  return response.data
}

/**
 * 清空对话历史
 */
export async function clearChatHistory(sessionId: string): Promise<{ success: boolean }> {
  const response = await apiClient.delete(`/api/chat/history/${sessionId}`)
  return response.data
}

// ===========================================
// 地图服务 API
// ===========================================

/**
 * 搜索 POI
 */
export async function searchPOI(keywords: string, city: string): Promise<{ success: boolean; data: unknown[] }> {
  const response = await apiClient.get('/api/map/poi', { params: { keywords, city } })
  return response.data
}

/**
 * 获取天气
 */
export async function getWeather(city: string): Promise<{ success: boolean; data: unknown[] }> {
  const response = await apiClient.get('/api/map/weather', { params: { city } })
  return response.data
}

/**
 * 获取静态地图图片
 */
export function getStaticMapUrl(city: string, markers?: string): string {
  let url = `${API_BASE_URL}/api/map/staticmap?city=${encodeURIComponent(city)}`
  if (markers) {
    url += `&markers=${encodeURIComponent(markers)}`
  }
  return url
}

// ===========================================
// 系统配置 API
// ===========================================

/**
 * 获取可用的 LLM 提供商
 */
export async function getLLMProviders(): Promise<{
  current: string
  available: Array<{ name: string; model: string }>
}> {
  const response = await apiClient.get('/api/config/llm-providers')
  return response.data
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ status: string }> {
  const response = await apiClient.get('/health')
  return response.data
}

export default apiClient
