// API 响应类型定义
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 用户相关接口响应类型
export interface UserInfo {
  id: number
  username: string
  email: string
  avatar?: string
  preferences?: {
    favoriteGenres?: string[]
    favoriteGames?: number[]
  }
}

export interface LoginResponse {
  token: string
  user: UserInfo
}

export interface RegisterData {
  username: string
  email: string
  password: string
}

export interface UpdateProfileData extends Partial<UserInfo> {
  password?: string
}

// 游戏相关接口响应类型
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

export interface GameListResponse {
  games: Game[]
  total: number
  page: number
  limit: number
}

export interface GameListParams {
  page?: number
  limit?: number
  tags?: string[]
  search?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}
