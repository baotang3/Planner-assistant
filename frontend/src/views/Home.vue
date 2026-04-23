<template>
  <div class="home-container">
    <!-- 头部 -->
    <div class="header">
      <h1>🌍 LangGraph 智能旅行助手</h1>
      <p>基于多 Agent 协作的智能行程规划系统</p>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：表单输入 -->
      <el-card class="form-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <el-icon><Location /></el-icon>
            <span>行程规划</span>
          </div>
        </template>

        <el-form :model="formData" label-position="top" @submit.prevent="handleSubmit">
          <!-- 城市和日期 -->
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="目的地城市" required>
                <el-input v-model="formData.city" placeholder="例如：北京、上海、成都">
                  <template #prefix>
                    <el-icon><Location /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="出发日期" required>
                <el-date-picker
                  v-model="formData.start_date"
                  type="date"
                  placeholder="选择日期"
                  style="width: 100%"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="返回日期" required>
                <el-date-picker
                  v-model="formData.end_date"
                  type="date"
                  placeholder="选择日期"
                  style="width: 100%"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 旅行天数显示 -->
          <el-alert
            v-if="travelDays > 0"
            :title="`共 ${travelDays} 天行程`"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px"
          />

          <!-- 偏好设置 -->
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="交通方式">
                <el-select v-model="formData.transportation" style="width: 100%">
                  <el-option label="🚇 公共交通" value="公共交通" />
                  <el-option label="🚗 自驾" value="自驾" />
                  <el-option label="🚶 步行" value="步行" />
                  <el-option label="🔀 混合" value="混合" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="住宿偏好">
                <el-select v-model="formData.accommodation" style="width: 100%">
                  <el-option label="💰 经济型酒店" value="经济型酒店" />
                  <el-option label="🏨 舒适型酒店" value="舒适型酒店" />
                  <el-option label="⭐ 豪华酒店" value="豪华酒店" />
                  <el-option label="🏡 民宿" value="民宿" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 旅行偏好 -->
          <el-form-item label="旅行偏好">
            <el-checkbox-group v-model="formData.preferences">
              <el-checkbox label="历史文化" border>🏛️ 历史文化</el-checkbox>
              <el-checkbox label="自然风光" border>🏞️ 自然风光</el-checkbox>
              <el-checkbox label="美食" border>🍜 美食</el-checkbox>
              <el-checkbox label="购物" border>🛍️ 购物</el-checkbox>
              <el-checkbox label="艺术" border>🎨 艺术</el-checkbox>
              <el-checkbox label="休闲" border>☕ 休闲</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <!-- 额外要求 -->
          <el-form-item label="额外要求">
            <el-input
              v-model="formData.free_text_input"
              type="textarea"
              :rows="3"
              placeholder="请输入您的额外要求，例如：想去看升旗、需要无障碍设施..."
            />
          </el-form-item>

          <!-- 预算设置 -->
          <el-form-item label="预算范围">
            <div class="budget-slider-container">
              <el-slider
                v-model="formData.budget"
                range
                :min="500"
                :max="10000"
                :step="100"
                :format-tooltip="(val: number) => `¥${val}`"
              />
              <div class="budget-display">
                <el-tag type="success">¥{{ formData.budget[0] }}</el-tag>
                <span> - </span>
                <el-tag type="warning">¥{{ formData.budget[1] }}</el-tag>
                <span class="budget-label">（{{ budgetLevel }}）</span>
              </div>
            </div>
          </el-form-item>

          <!-- LLM 选择 -->
          <el-form-item label="AI 模型">
            <el-radio-group v-model="formData.llm_provider">
              <el-radio label="deepseek">DeepSeek</el-radio>
              <el-radio label="aliyun">阿里云百炼</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              v-if="!isLoading"
              type="primary"
              size="large"
              @click="handleSubmit"
              style="width: 100%"
            >
              <el-icon><Promotion /></el-icon>
              开始规划行程
            </el-button>
            <el-button
              v-else
              type="danger"
              size="large"
              @click="handleStop"
              style="width: 100%"
            >
              <el-icon><Close /></el-icon>
              终止规划
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 右侧：执行进度 -->
      <el-card v-if="isLoading || steps.length > 0" class="progress-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <el-icon><Loading /></el-icon>
            <span>Agent 执行进度</span>
          </div>
        </template>

        <el-timeline>
          <el-timeline-item
            v-for="(step, index) in steps"
            :key="index"
            :type="getStepType(step.status)"
            :title="step.node"
          >
            <div class="step-content">
              <div class="step-header">
                <span class="step-name">{{ getNodeName(step.node) }}</span>
                <el-tag :type="getStepType(step.status)" size="small">
                  {{ step.status }}
                </el-tag>
              </div>
              <div v-if="step.message" class="step-message">
                {{ step.message }}
              </div>
              <div v-if="step.error" class="step-error">
                <el-icon><WarningFilled /></el-icon>
                {{ step.error }}
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>

        <!-- 当前状态提示 -->
        <div v-if="isLoading && currentMessage" class="current-status">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ currentMessage }}</span>
        </div>

        <el-progress
          v-if="isLoading"
          :percentage="progress"
          :status="progressStatus"
          :stroke-width="10"
          style="margin-top: 20px"
        />
      </el-card>
    </div>

    <!-- 底部链接 -->
    <div class="footer">
      <el-button text @click="$router.push('/chat')">
        <el-icon><ChatDotRound /></el-icon>
        切换到对话模式
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Location, Promotion, Loading, WarningFilled, ChatDotRound, Close } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useTripStore } from '@/stores/trip'
import type { TripRequest, AgentStep } from '@/types'

const router = useRouter()
const tripStore = useTripStore()

const formData = ref<TripRequest>({
  city: '',
  start_date: '',
  end_date: '',
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: '',
  llm_provider: 'deepseek',
  budget: [1000, 3000] as [number, number]
})

const isLoading = ref(false)
const isStopped = ref(false)
const steps = ref<AgentStep[]>([])
const progress = ref(0)
const currentStep = ref('')
const currentMessage = ref('')
const abortController = ref<AbortController | null>(null)

// 计算旅行天数
const travelDays = computed(() => {
  if (formData.value.start_date && formData.value.end_date) {
    const start = dayjs(formData.value.start_date)
    const end = dayjs(formData.value.end_date)
    const days = end.diff(start, 'day') + 1
    return days > 0 ? days : 0
  }
  return 0
})

// 预算等级
const budgetLevel = computed(() => {
  const max = formData.value.budget[1]
  if (max <= 1500) return '经济出行'
  if (max <= 3000) return '舒适旅行'
  if (max <= 5000) return '品质游玩'
  if (max <= 8000) return '高端体验'
  return '奢华之旅'
})

// 监听日期变化
watch(travelDays, (days) => {
  formData.value.travel_days = days
})

// 进度状态
const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success'
  if (progress.value >= 80) return 'warning'
  return ''
})

// 获取步骤类型
function getStepType(status: string): 'primary' | 'success' | 'danger' | 'info' {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

// 获取节点名称
function getNodeName(node: string): string {
  const names: Record<string, string> = {
    'init': '🚀 初始化',
    'poi_search': '🔍 景点搜索',
    'weather': '🌤️ 天气查询',
    'hotel': '🏨 酒店推荐',
    'planner': '📋 行程规划',
    'human_review': '👤 等待审核',
    'complete': '✅ 完成',
    'stopped': '⏹️ 已终止',
    'error': '❌ 错误'
  }
  return names[node] || node
}

// 提交表单
async function handleSubmit() {
  if (!formData.value.city || !formData.value.start_date || !formData.value.end_date) {
    ElMessage.warning('请填写完整信息')
    return
  }

  isLoading.value = true
  isStopped.value = false
  steps.value = []
  progress.value = 0
  currentStep.value = '正在准备...'
  currentMessage.value = '正在初始化...'

  const sessionId = `session_${Date.now()}`
  tripStore.setSessionId(sessionId)

  // 创建 AbortController 用于取消请求
  abortController.value = new AbortController()

  try {
    // 使用流式API获取实时反馈
    const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000'
    const response = await fetch(`${baseUrl}/api/trip/plan/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...formData.value, session_id: sessionId }),
      signal: abortController.value.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      if (isStopped.value) {
        reader.cancel()
        break
      }

      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleStreamEvent(data)
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }

    // 处理剩余的buffer
    if (buffer.startsWith('data: ')) {
      try {
        const data = JSON.parse(buffer.slice(6))
        handleStreamEvent(data)
      } catch (e) {
        console.error('Failed to parse remaining SSE data:', e)
      }
    }

  } catch (error: any) {
    if (error.name === 'AbortError') {
      ElMessage.info('已终止规划')
      steps.value.push({ node: 'stopped', status: 'failed', message: '用户终止' })
    } else {
      console.error('[Home] 请求错误:', error)
      ElMessage.error(error.message || '请求失败')
      tripStore.addError(error.message)
      steps.value.push({ node: 'error', status: 'failed', error: error.message })
    }
  } finally {
    isLoading.value = false
    abortController.value = null
  }
}

// 处理流式事件
function handleStreamEvent(data: any) {
  console.log('[Home] 收到事件:', data)

  // 更新当前消息
  if (data.message) {
    currentMessage.value = data.message
  }

  // 更新进度
  if (data.step) {
    progress.value = Math.min(data.step * 10, 90)
  }

  // 更新步骤列表
  if (data.node) {
    const existingIndex = steps.value.findIndex(s => s.node === data.node)
    const step: AgentStep = {
      node: data.node,
      status: data.status,
      message: data.message,
      data: data.data
    }

    if (existingIndex >= 0) {
      steps.value[existingIndex] = step
    } else {
      steps.value.push(step)
    }
  }

  // 处理完成
  if (data.node === 'complete' && data.status === 'completed') {
    progress.value = 100

    if (data.data?.itinerary) {
      tripStore.setTripPlan(data.data.itinerary as any)
      tripStore.setStatus('completed')
      tripStore.setNeedHumanReview(false)

      ElMessage.success('行程规划完成！')

      setTimeout(() => {
        router.push('/result')
      }, 500)
    }
  }

  // 处理错误
  if (data.status === 'failed' || data.node === 'error') {
    ElMessage.error(data.message || '规划失败')
  }
}

// 终止规划
function handleStop() {
  if (abortController.value) {
    isStopped.value = true
    abortController.value.abort()
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
}

.header {
  text-align: center;
  margin-bottom: 40px;
  color: white;
}

.header h1 {
  font-size: 36px;
  margin-bottom: 10px;
}

.header p {
  font-size: 16px;
  opacity: 0.9;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
}

@media (max-width: 900px) {
  .main-content {
    grid-template-columns: 1fr;
  }
}

.form-card, .progress-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.step-content {
  padding: 8px 0;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-name {
  font-weight: 500;
}

.step-error {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.step-message {
  color: #606266;
  font-size: 13px;
  margin-top: 4px;
}

.current-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 8px;
  color: #409eff;
  font-size: 14px;
  margin-top: 12px;
}

.current-status .el-icon {
  font-size: 16px;
}

.budget-slider-container {
  width: 100%;
}

.budget-display {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  justify-content: center;
}

.budget-label {
  color: #909399;
  font-size: 13px;
}

.footer {
  text-align: center;
  margin-top: 30px;
}

.footer .el-button {
  color: white;
}
</style>
