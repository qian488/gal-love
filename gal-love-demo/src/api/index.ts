import axios from 'axios'
import type {
  BackupInfo,
  BackupResult,
  DuplicateCandidate,
  Entry,
  EntryInput,
  EntryListResponse,
  FeedbackInput,
  HealthResponse,
  ImportBangumiInput,
  ImportScheduledResponse,
  ImportVndbInput,
  ManualWorkInput,
  MergeResult,
  PairwiseAnswerInput,
  PairwiseAnswerResponse,
  PairwiseNextResponse,
  PersonaDetailResponse,
  PersonaProviderListResponse,
  RecommendationQuery,
  RecommendationResponse,
  RestoreResult,
  Settings,
  SettingsPatch,
  Stats,
  SyncRunListResponse,
  TagListResponse,
  TarotDrawResponse,
  TasteQuizResponse,
  VotesImportInput,
  VotesImportResult,
  VotesStats,
  Work,
  WorkListResponse,
  WorkQuery,
} from '../types/api'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data
    let message = '网络错误，请确认 gal-love-core 已运行在 8000 端口'
    if (typeof data?.detail === 'string') {
      message = data.detail
    } else if (Array.isArray(data?.detail)) {
      message = data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('；')
    } else if (error.response) {
      message = `请求失败（${error.response.status}）`
    } else if (error.code === 'ECONNABORTED') {
      message = '请求超时，请稍后重试'
    }
    return Promise.reject(new Error(message))
  },
)

async function get<T>(url: string, params?: object): Promise<T> {
  const response = await http.get(url, { params })
  return response.data as T
}

async function post<T>(url: string, data?: unknown): Promise<T> {
  const response = await http.post(url, data)
  return response.data as T
}

async function put<T>(url: string, data?: unknown): Promise<T> {
  const response = await http.put(url, data)
  return response.data as T
}

async function remove<T>(url: string): Promise<T> {
  const response = await http.delete(url)
  return response.data as T
}

export const api = {
  health: () => get<HealthResponse>('/health'),
  stats: () => get<Stats>('/stats'),

  works: (params: WorkQuery = {}) => get<WorkListResponse>('/works', params),
  work: (id: number) => get<Work>(`/works/${id}`),
  similar: (id: number, limit = 8) => get<{ items: Work[] }>(`/works/${id}/similar`, { limit }),
  tags: (params: { q?: string; limit?: number } = {}) => get<TagListResponse>('/tags', params),

  recommendations: (params: RecommendationQuery = {}) =>
    get<RecommendationResponse>('/recommendations', params),

  tasteQuiz: () => get<TasteQuizResponse>('/taste-quiz'),
  saveTasteQuiz: (answers: Record<string, string>) =>
    post<TasteQuizResponse>('/taste-quiz', { answers }),

  // 画像体系：列表 / 详情 / 提交 / 二选一 / 塔罗
  personaProviders: () => get<PersonaProviderListResponse>('/persona/providers'),
  persona: (key: string) => get<PersonaDetailResponse>(`/persona/${key}`),
  savePersona: (key: string, answers: Record<string, string>) =>
    post<PersonaDetailResponse>(`/persona/${key}`, { answers }),
  pairwiseNext: (count = 1, includeNsfw = false) =>
    get<PairwiseNextResponse>('/persona/pairwise/next', {
      count,
      include_nsfw: includeNsfw,
    }),
  pairwiseAnswer: (data: PairwiseAnswerInput) =>
    post<PairwiseAnswerResponse>('/persona/pairwise/answer', data),
  pairwiseReset: () => post<PersonaDetailResponse>('/persona/pairwise/reset'),
  tarotDraw: (spread = 1, seed?: string) =>
    post<TarotDrawResponse>('/persona/tarot/draw', { spread, seed }),

  entries: () => get<EntryListResponse>('/me/entries'),
  saveEntry: (workId: number, data: EntryInput) => put<Work>(`/me/entries/${workId}`, data),
  deleteEntry: (workId: number) => remove<{ ok: boolean }>(`/me/entries/${workId}`),

  feedback: (data: FeedbackInput) => post<{ ok: boolean }>('/feedback', data),

  settings: () => get<Settings>('/settings'),
  saveSettings: (data: SettingsPatch) => put<Settings>('/settings', data),

  createWork: (data: ManualWorkInput) => post<Work>('/admin/works', data),
  importVndb: (data: ImportVndbInput) =>
    post<ImportScheduledResponse>('/admin/import/vndb', data),
  importBangumi: (data: ImportBangumiInput) =>
    post<ImportScheduledResponse>('/admin/import/bangumi', data),
  syncRuns: (limit = 10) => get<SyncRunListResponse>('/admin/sync-runs', { limit }),

  // 数据治理：重复检测与合并
  duplicates: (limit = 50, minScore = 0.75) =>
    get<{ items: DuplicateCandidate[] }>('/admin/duplicates', { limit, min_score: minScore }),
  mergeWorks: (sourceId: number, targetId: number) =>
    post<MergeResult>('/admin/works/merge', { source_id: sourceId, target_id: targetId }),

  // 备份与恢复
  backups: () => get<{ items: BackupInfo[] }>('/admin/backups'),
  createBackup: () => post<BackupResult>('/admin/backup'),
  restoreBackup: (filename: string) =>
    post<RestoreResult>('/admin/restore', { filename }),

  // VNDB 票数库
  votesStats: () => get<VotesStats>('/admin/votes/stats'),
  importVotes: (data: VotesImportInput) =>
    post<VotesImportResult>('/admin/votes/import', data),
}

export const entryStatusLabels: Record<Entry['status'], string> = {
  want: '想玩',
  playing: '在玩',
  finished: '玩过',
  dropped: '弃坑',
}

export const entryStatusColors: Record<Entry['status'], string> = {
  want: '#409eff',
  playing: '#e6a23c',
  finished: '#67c23a',
  dropped: '#909399',
}

export default api
