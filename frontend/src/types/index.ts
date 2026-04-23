// TypeScript 类型定义

export interface Location {
  longitude: number
  latitude: number
}

export interface POI {
  id: string
  name: string
  address: string
  location: Location
  category?: string
  rating?: number
  tel?: string
  ticket_price?: number
  visit_duration?: number
  description?: string
  image_url?: string
}

export interface Weather {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number | string
  night_temp: number | string
  wind_direction: string
  wind_power: string
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  type: string
  estimated_cost?: number
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner'
  name: string
  address?: string
  description?: string
  estimated_cost?: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  ticket_price?: number
}

export interface DayPlan {
  date: string
  day_index: number
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: Weather[]
  overall_suggestions: string
  budget?: Budget
}

export interface TripRequest {
  session_id?: string
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input?: string
  llm_provider?: string
  budget: [number, number]
}

export interface TripPlanResponse {
  success: boolean
  message: string
  data?: TripPlan
  status: TripStatus
}

export type TripStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'need_confirm'

export interface AgentStep {
  node: string
  status: string
  message?: string
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  duration_ms?: number
  error?: string
  data?: Record<string, unknown>
}

export interface StreamingResponse {
  session_id: string
  step: number
  node: string
  status: TripStatus
  message: string
  data?: Record<string, unknown>
  thought?: string
  steps: AgentStep[]
}

export interface ChatMessage {
  session_id: string
  message: string
  message_type?: string
  llm_provider?: string
}

export interface ChatResponse {
  session_id: string
  response: string
  trip_plan?: TripPlan
}

export interface UserFeedback {
  session_id: string
  action: 'approve' | 'modify' | 'reject'
  modifications?: Record<string, unknown>
  comment?: string
}

export interface LLMProvider {
  name: string
  model: string
}
