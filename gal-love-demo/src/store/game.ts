import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Game, GameListResponse } from '../types/api'
import { gameApi } from '../api'
import { ElMessage } from 'element-plus'

export interface GameFilter {
  page: number
  pageSize: number
  sortBy: string
  sortOrder: 'asc' | 'desc'
  tags?: string[]
  search?: string
}

export const useGameStore = defineStore('game', () => {
  const games = ref<Game[]>([])
  const loading = ref(false)
  const total = ref(0)
  const currentGame = ref<Game | null>(null)
  const recommendations = ref<Game[]>([])
  const currentFilter = ref<GameFilter>({
    page: 1,
    pageSize: 12,
    sortBy: 'rating',
    sortOrder: 'desc'
  })

  const filteredGames = computed(() => {
    let filtered = [...games.value]
    
    if (currentFilter.value.search) {
      const query = currentFilter.value.search.toLowerCase()
      filtered = filtered.filter(game => 
        game.title.toLowerCase().includes(query) ||
        game.description.toLowerCase().includes(query)
      )
    }

    if (currentFilter.value.tags?.length) {
      filtered = filtered.filter(game =>
        currentFilter.value.tags!.every(tag => game.tags.includes(tag))
      )
    }

    // 排序
    filtered.sort((a, b) => {
      const factor = currentFilter.value.sortOrder === 'asc' ? 1 : -1
      switch (currentFilter.value.sortBy) {
        case 'rating':
          return (a.rating - b.rating) * factor
        case 'releaseDate':
          return (new Date(a.releaseDate).getTime() - new Date(b.releaseDate).getTime()) * factor
        case 'title':
          return a.title.localeCompare(b.title) * factor
        default:
          return 0
      }
    })

    return filtered
  })

  async function fetchGames() {
    loading.value = true
    try {
      const { data } = await gameApi.getGames({ 
        page: currentFilter.value.page, 
        limit: currentFilter.value.pageSize,
        tags: currentFilter.value.tags,
        search: currentFilter.value.search
      })
      games.value = data.games
      total.value = data.total
    } catch (error: any) {
      ElMessage.error(error.message || '获取游戏列表失败')
    } finally {
      loading.value = false
    }
  }

  async function fetchGameDetail(id: string) {
    loading.value = true
    try {
      const { data } = await gameApi.getGameDetail(id)
      currentGame.value = data
    } catch (error: any) {
      ElMessage.error(error.message || '获取游戏详情失败')
    } finally {
      loading.value = false
    }
  }

  async function fetchRecommendations() {
    try {
      const { data } = await gameApi.getRecommendations()
      recommendations.value = data
    } catch (error: any) {
      console.error('获取推荐失败:', error)
    }
  }

  async function rateGame(gameId: string, rating: number) {
    try {
      await gameApi.rateGame(gameId, rating)
      if (currentGame.value && currentGame.value.id.toString() === gameId) {
        currentGame.value.userRating = rating
      }
      ElMessage.success('评分成功')
    } catch (error: any) {
      ElMessage.error(error.message || '评分失败')
    }
  }

  function updateFilter(filter: Partial<GameFilter>) {
    currentFilter.value = {
      ...currentFilter.value,
      ...filter,
      // 当过滤条件改变时，重置页码
      ...(filter.search || filter.tags ? { page: 1 } : {})
    }
    fetchGames()
  }

  function clearFilter() {
    currentFilter.value = {
      page: 1,
      pageSize: 12,
      sortBy: 'rating',
      sortOrder: 'desc'
    }
    fetchGames()
  }

  return {
    games,
    loading,
    total,
    currentGame,
    recommendations,
    currentFilter,
    filteredGames,
    fetchGames,
    fetchGameDetail,
    fetchRecommendations,
    rateGame,
    updateFilter,
    clearFilter
  }
})
