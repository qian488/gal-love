import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type {
  Entry,
  EntryInput,
  EntryStatus,
  RecommendationQuery,
  Settings,
  SettingsPatch,
  Stats,
  Work,
} from '../types/api'

/** 推荐请求参数：在后端 RecommendationQuery 之上允许显式指定算法版本。 */
export type RecommendationParams = RecommendationQuery & { algorithm?: string }

const defaultSettings: Settings = {
  include_nsfw: false,
  min_year: null,
  max_length_minutes: null,
  platform: null,
  language: null,
  diversity: 0.15,
  quiz_merge_home: true,
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : '请求失败'
}

export const useCatalogStore = defineStore('catalog', () => {
  const recommendations = ref<Work[]>([])
  const entries = ref<Work[]>([])
  const settings = ref<Settings>({ ...defaultSettings })
  const stats = ref<Stats | null>(null)
  const algorithmVersion = ref('content-v1')
  const loadingRecommendations = ref(false)
  const loadingEntries = ref(false)

  const entryMap = computed(() => {
    const map = new Map<number, Entry>()
    for (const work of entries.value) {
      if (work.entry) map.set(work.id, work.entry)
    }
    return map
  })

  const entryCounts = computed<Record<EntryStatus, number>>(() => {
    const counts: Record<EntryStatus, number> = {
      want: 0,
      playing: 0,
      finished: 0,
      dropped: 0,
    }
    for (const entry of entryMap.value.values()) {
      counts[entry.status] += 1
    }
    return counts
  })

  // 至少 3 部「已评分 / 已玩 / 收藏」作品才算建立口味画像，
  // 与首页「给 3–5 部喜欢的作品评分」的文案保持一致。
  const hasProfile = computed(
    () =>
      entries.value.filter((work) => {
        const entry = work.entry
        if (!entry) return false
        return (
          entry.favorite ||
          entry.status === 'finished' ||
          entry.status === 'playing' ||
          (entry.rating ?? 0) > 0
        )
      }).length >= 3,
  )

  const tasteTags = computed(() => {
    const weights = new Map<string, number>()
    for (const work of entries.value) {
      const entry = work.entry
      if (!entry) continue
      const positive =
        entry.favorite ||
        entry.status === 'finished' ||
        (entry.rating ?? 0) >= 7.5
      if (!positive) continue
      const weight = entry.favorite ? 2 : 1
      for (const tag of work.tags.slice(0, 10)) {
        weights.set(tag.name, (weights.get(tag.name) ?? 0) + weight)
      }
    }
    return [...weights.entries()]
      .sort((left, right) => right[1] - left[1])
      .slice(0, 8)
      .map(([name, count]) => ({ name, count }))
  })

  function entryFor(workId: number): Entry | null {
    return entryMap.value.get(workId) ?? null
  }

  // 兼容旧调用：fetchRecommendations(12) 等价于传 { limit: 12 }；
  // 新调用可传入与设置一致的参数对象，缺省 limit 时仍按 12 处理。
  async function fetchRecommendations(params: number | RecommendationParams = 12) {
    const query: RecommendationParams =
      typeof params === 'number' ? { limit: params } : { ...params }
    if (query.limit === undefined) query.limit = 12

    loadingRecommendations.value = true
    try {
      const data = await api.recommendations(query)
      recommendations.value = data.items
      algorithmVersion.value = data.algorithm_version
    } catch (error) {
      ElMessage.error(messageOf(error))
    } finally {
      loadingRecommendations.value = false
    }
  }

  async function fetchEntries() {
    loadingEntries.value = true
    try {
      entries.value = (await api.entries()).items
    } catch (error) {
      ElMessage.error(messageOf(error))
    } finally {
      loadingEntries.value = false
    }
  }

  async function fetchSettings() {
    try {
      settings.value = await api.settings()
    } catch (error) {
      ElMessage.error(messageOf(error))
    }
  }

  async function saveSettings(patch: SettingsPatch) {
    settings.value = await api.saveSettings(patch)
    return settings.value
  }

  async function loadStats() {
    try {
      const health = await api.health()
      stats.value = health.stats
      algorithmVersion.value = health.algorithm
    } catch {
      stats.value = null
    }
  }

  async function saveEntry(workId: number, data: EntryInput) {
    const work = await api.saveEntry(workId, data)
    await fetchEntries()
    return work
  }

  async function removeEntry(workId: number) {
    await api.deleteEntry(workId)
    await fetchEntries()
  }

  async function markNotInterested(workId: number) {
    await api.feedback({ work_id: workId, kind: 'not_interested' })
    recommendations.value = recommendations.value.filter((work) => work.id !== workId)
  }

  return {
    recommendations,
    entries,
    settings,
    stats,
    algorithmVersion,
    loadingRecommendations,
    loadingEntries,
    entryMap,
    entryCounts,
    hasProfile,
    tasteTags,
    entryFor,
    fetchRecommendations,
    fetchEntries,
    fetchSettings,
    saveSettings,
    loadStats,
    saveEntry,
    removeEntry,
    markNotInterested,
  }
})
