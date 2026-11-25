export type EntryStatus = 'want' | 'playing' | 'finished' | 'dropped'
export type FeedbackKind = 'not_interested' | 'like' | 'dislike' | 'seen'

export interface WorkTag {
  name: string
  name_zh?: string | null
  aliases?: string[]
  category?: string | null
  weight: number
  spoiler?: number
  source?: string
}

export interface WorkTitle {
  lang: string
  title: string
  latin?: string | null
  official?: number | boolean
  is_main?: number | boolean
  source?: string
}

export interface ExternalRef {
  source: string
  external_id: string
  url?: string | null
  fetched_at?: string
}

export interface Entry {
  work_id?: number
  status: EntryStatus
  rating: number | null
  favorite: boolean
  notes: string | null
  started_at?: string | null
  finished_at?: string | null
  updated_at?: string
}

export interface Work {
  id: number
  title: string
  title_zh?: string | null
  original_title?: string | null
  romanized_title?: string | null
  description?: string | null
  cover_url?: string | null
  release_date?: string | null
  release_year?: number | null
  length_minutes?: number | null
  length_label?: number | null
  platforms: string[]
  languages: string[]
  vndb_rating?: number | null
  vndb_votecount?: number | null
  bangumi_rating?: number | null
  bangumi_votecount?: number | null
  rating?: number | null
  rating_count?: number | null
  nsfw: boolean
  source: string
  created_at?: string
  updated_at?: string
  tags: WorkTag[]
  companies: string[]
  titles?: WorkTitle[]
  external_refs?: ExternalRef[]
  entry?: Entry | null
  score?: number
  reason?: string
  shared_tags?: string[]
  algorithm_version?: string
  profile_source?: ProfileSource
}

export interface WorkListResponse {
  items: Work[]
  total: number
  page: number
  limit: number
}

export type ProfileSource = 'auto' | 'library' | 'quiz' | 'all'

export interface TasteQuizOption {
  id: string
  label: string
  tags?: Record<string, number>
  axes?: Record<string, number>
  year?: number
  length?: number
}

export interface TasteQuizQuestion {
  id: string
  title: string
  subtitle?: string
  options: TasteQuizOption[]
}

export interface TasteQuizResult {
  code: string
  labels: string[]
  tags: Record<string, number>
  year_center: number | null
  length_center: number | null
  completed: boolean
}

export interface TasteQuizResponse {
  questions: TasteQuizQuestion[]
  answers: Record<string, string>
  result: TasteQuizResult
}

export interface RecommendationResponse {
  items: Work[]
  batch_id: string | null
  algorithm_version: string
  profile_source: ProfileSource
}

export interface TagInfo {
  id: number
  name: string
  name_zh?: string | null
  aliases?: string[]
  category?: string | null
  work_count: number
}

export interface TagListResponse {
  items: TagInfo[]
}

export interface EntryListResponse {
  items: Work[]
}

export interface EntryInput {
  status?: EntryStatus
  rating?: number | null
  favorite?: boolean
  notes?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export interface FeedbackInput {
  work_id: number
  kind: FeedbackKind
  note?: string | null
}

export interface Settings {
  include_nsfw: boolean
  min_year: number | null
  max_length_minutes: number | null
  platform: string | null
  language: string | null
  diversity: number
  quiz_merge_home: boolean
}

export type SettingsPatch = Partial<Settings>

export interface Stats {
  works: number
  tags: number
  companies: number
  entries: number
  feedback: number
  recommendations: number
  sync_runs: number
}

export interface HealthResponse {
  status: string
  db: string
  stats: Stats
  algorithm: string
}

export interface WorkQuery {
  q?: string
  tag?: string
  status?: EntryStatus | 'none'
  min_rating?: number
  sort?: 'rating' | 'votes' | 'release' | 'title' | 'random'
  page?: number
  limit?: number
  include_nsfw?: boolean
  platform?: string
  language?: string
  min_year?: number
  max_length_minutes?: number
}

export type RecommendationAlgorithm = 'auto' | 'content' | 'hybrid'

export interface RecommendationQuery {
  limit?: number
  include_nsfw?: boolean
  min_year?: number
  max_length_minutes?: number
  platform?: string
  language?: string
  diversity?: number
  save?: boolean
  algorithm?: RecommendationAlgorithm
  profile_source?: ProfileSource
}

export interface SyncRun {
  id: number
  source: string
  status: string
  started_at: string
  finished_at?: string | null
  stats: Record<string, unknown>
  error?: string | null
}

export interface SyncRunListResponse {
  items: SyncRun[]
}

export interface ManualWorkInput {
  title: string
  title_zh?: string | null
  original_title?: string | null
  description?: string | null
  cover_url?: string | null
  release_date?: string | null
  length_minutes?: number | null
  length_label?: number | null
  platforms?: string[]
  languages?: string[]
  rating?: number | null
  nsfw?: boolean
  tags?: string[]
  companies?: string[]
}

export interface ImportVndbInput {
  limit?: number
  min_votes?: number
  wait?: boolean
  incremental?: boolean
}

export interface ImportBangumiInput {
  limit?: number
  avg_only?: boolean
  wait?: boolean
  incremental?: boolean
}

export interface ImportScheduledResponse {
  status: string
  run_id: number
}

/** 疑似重复的作品对，来自 GET /api/admin/duplicates。 */
export interface DuplicateCandidate {
  work_id: number
  other_id: number
  score: number
  reasons: string[]
}

/** POST /api/admin/works/merge 的返回结果，moved 为各表实际迁移条数。 */
export interface MergeResult {
  ok: boolean
  source_id: number
  target_id: number
  moved: Record<string, number>
}

/** 单个备份文件的元信息。 */
export interface BackupInfo {
  filename: string
  path: string
  size_bytes: number
  created_at: string
}

/** POST /api/admin/backup 新建备份后返回的备份信息。 */
export type BackupResult = BackupInfo

/** POST /api/admin/restore 的返回结果，auto_backup 为恢复前的安全备份。 */
export interface RestoreResult {
  ok: boolean
  db_path: string
  backup_path: string
  filename: string
  size_bytes: number
  auto_backup: BackupInfo
}

/** GET /api/admin/votes/stats 返回的票数库统计。 */
export interface VotesStats {
  path: string
  available: boolean
  votes: number
  users: number
  items: number
  mean_score: number | null
  min_vote_count: number
  max_vote_count: number
}

/** POST /api/admin/votes/import 的请求体。 */
export interface VotesImportInput {
  dump_path: string
  min_votes?: number
  limit?: number
}

/** POST /api/admin/votes/import 返回的导入统计。 */
export interface VotesImportResult {
  dump: string
  db: string
  lines: number
  parsed: number
  skipped: number
  comments: number
  min_votes: number
  limit: number | null
  candidates: number
  items_imported: number
  votes_imported: number
  imported: number
  users: number
}
