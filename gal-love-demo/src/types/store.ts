import type { UserInfo } from './api'

export interface UserState {
  userInfo: UserInfo | null
  isLoggedIn: boolean
  loading: boolean
}

export interface GameState {
  games: Game[]
  loading: boolean
  total: number
  currentGame: Game | null
  recommendations: Game[]
  currentFilter: GameFilter
}

export interface Game {
  id: number
  title: string
  description: string
  coverImage: string
  releaseDate: string
  developer: string
  publisher: string
  genres: string[]
  tags: string[]
  rating: number
  userRating?: number
  price: number
  platform: string[]
  languages: string[]
  screenshots: string[]
}

export interface GameFilter {
  page: number
  pageSize: number
  sortBy: string
  sortOrder: 'asc' | 'desc'
  tags?: string[]
  search?: string
}
