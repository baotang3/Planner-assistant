import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { TripPlan, AgentStep, TripStatus } from '@/types'

export const useTripStore = defineStore('trip', () => {
  // 状态
  const sessionId = ref<string>('')
  const tripPlan = ref<TripPlan | null>(null)
  const status = ref<TripStatus>('pending')
  const currentStep = ref<string>('')
  const steps = ref<AgentStep[]>([])
  const errors = ref<string[]>([])
  const needHumanReview = ref(false)

  // 计算属性
  const isProcessing = computed(() => status.value === 'processing')
  const isCompleted = computed(() => status.value === 'completed')
  const hasErrors = computed(() => errors.value.length > 0)

  // 方法
  function setSessionId(id: string) {
    sessionId.value = id
  }

  function setTripPlan(plan: TripPlan | null) {
    tripPlan.value = plan
  }

  function setStatus(newStatus: TripStatus) {
    status.value = newStatus
  }

  function setCurrentStep(step: string) {
    currentStep.value = step
  }

  function addStep(step: AgentStep) {
    steps.value.push(step)
  }

  function setSteps(newSteps: AgentStep[]) {
    steps.value = newSteps
  }

  function addError(error: string) {
    errors.value.push(error)
  }

  function setErrors(newErrors: string[]) {
    errors.value = newErrors
  }

  function setNeedHumanReview(need: boolean) {
    needHumanReview.value = need
  }

  function reset() {
    sessionId.value = ''
    tripPlan.value = null
    status.value = 'pending'
    currentStep.value = ''
    steps.value = []
    errors.value = []
    needHumanReview.value = false
  }

  return {
    // 状态
    sessionId,
    tripPlan,
    status,
    currentStep,
    steps,
    errors,
    needHumanReview,
    // 计算属性
    isProcessing,
    isCompleted,
    hasErrors,
    // 方法
    setSessionId,
    setTripPlan,
    setStatus,
    setCurrentStep,
    addStep,
    setSteps,
    addError,
    setErrors,
    setNeedHumanReview,
    reset
  }
})
