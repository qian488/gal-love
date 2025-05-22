export interface Game {
  id: number
  title: string
  originalTitle?: string
  coverImage: string
  description: string
  developer: string
  publisher: string
  releaseDate: string
  tags: string[]
  rating: number
  totalRatings: number
  price?: number
  platform: string[]
}

export interface GameListResponse {
  games: Game[]
  total: number
  page: number
  pageSize: number
}

export interface GameFilter {
  searchTerm?: string
  tags?: string[]
  platform?: string[]
  sortBy?: 'rating' | 'releaseDate' | 'title'
  sortOrder?: 'asc' | 'desc'
  page: number
  pageSize: number
}
