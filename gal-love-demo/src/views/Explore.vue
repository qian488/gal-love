<template>
  <div class="explore">
    <header class="page-head">
      <div>
        <span class="eyebrow">CATALOG</span>
        <h1>探索作品</h1>
        <p>所有视觉小说 / AVG 都在这里。按标题、中文名、标签或口碑找到下一部。</p>
      </div>
      <el-tag round effect="plain">{{ total }} 部结果</el-tag>
    </header>

    <section class="filters">
      <div class="search-wrap">
        <el-input
          v-model="searchInput"
          class="search"
          placeholder="搜索标题、中文名、别名、罗马音…"
          clearable
          @focus="panelOpen = true"
          @blur="onSearchBlur"
          @keyup.enter="onEnter"
          @clear="onClear"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <div v-if="panelOpen" class="search-panel" @mousedown.prevent>
          <template v-if="searchInput.trim()">
            <div v-if="suggestions.length" class="panel-section">
              <div class="panel-title">搜索建议</div>
              <button
                v-for="item in suggestions"
                :key="item.id"
                class="panel-row"
                type="button"
                @click="chooseSuggestion(item)"
              >
                <span class="row-text">{{ displayTitle(item) }}</span>
                <span v-if="item.release_year" class="row-meta">{{ item.release_year }}</span>
              </button>
            </div>
            <div v-else class="panel-empty">按回车搜索 “{{ searchInput.trim() }}”</div>
          </template>

          <template v-else>
            <div v-if="history.length" class="panel-section">
              <div class="panel-title">
                <span>最近搜索</span>
                <button class="link-btn" type="button" @click="clearHistory">清空</button>
              </div>
              <div class="history-list">
                <span v-for="word in history" :key="word" class="history-chip" @click="chooseHistory(word)">
                  {{ word }}
                  <el-icon class="chip-close" @click.stop="removeHistory(word)"><Close /></el-icon>
                </span>
              </div>
            </div>
          </template>

          <div v-if="hotTags.length" class="panel-section hot-tags">
            <div class="panel-title">热门标签</div>
            <div class="history-list">
              <el-tag
                v-for="item in hotTags"
                :key="item.id"
                effect="plain"
                round
                class="hot-tag"
                @click="chooseTag(item)"
              >
                {{ tagNameZh(item) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <el-select
        v-model="tag"
        class="filter-select tag-select"
        placeholder="全部标签"
        clearable
        filterable
        @change="onFilterChange"
      >
        <el-option
          v-for="item in tags"
          :key="item.id"
          :label="tagFilterLabel(item)"
          :value="item.name"
        >
          <span>{{ tagNameZh(item) }}</span>
          <span v-if="item.name !== tagNameZh(item)" class="option-alias">{{ item.name }}</span>
          <span class="option-count">{{ item.work_count }}</span>
        </el-option>
      </el-select>

      <el-select
        v-model="platform"
        class="filter-select platform-select"
        placeholder="全部平台"
        clearable
        @change="onFilterChange"
      >
        <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-select
        v-model="language"
        class="filter-select language-select"
        placeholder="全部语言"
        clearable
        @change="onFilterChange"
      >
        <el-option v-for="item in languageOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-select
        v-model="minYear"
        class="filter-select year-select"
        placeholder="最早年份"
        clearable
        @change="onFilterChange"
      >
        <el-option v-for="year in yearOptions" :key="year" :label="`${year} 年以后`" :value="year" />
      </el-select>

      <el-select
        v-model="maxLength"
        class="filter-select length-select"
        placeholder="最长时长"
        clearable
        @change="onFilterChange"
      >
        <el-option v-for="min in lengthOptions" :key="min" :label="`≤ ${min} 分钟`" :value="min" />
      </el-select>

      <el-select v-model="sort" class="filter-select sort-select" @change="onFilterChange">
        <el-option label="按评分" value="rating" />
        <el-option label="按人气" value="votes" />
        <el-option label="按发售时间" value="release" />
        <el-option label="按标题" value="title" />
        <el-option label="随机" value="random" />
      </el-select>

      <div class="switch-field">
        <span>内容范围</span>
        <el-select v-model="nsfwPolicy" class="filter-select" @change="onFilterChange">
          <el-option label="仅全年龄" value="off" />
          <el-option label="含成人剧情作" value="story" />
          <el-option label="全部内容" value="all" />
        </el-select>
      </div>

      <el-button @click="resetFilters">重置</el-button>
    </section>

    <div v-loading="loading" class="results">
      <div v-if="works.length" class="grid">
        <WorkCard
          v-for="work in displayWorks"
          :key="work.id"
          :work="work"
          :reason="true"
          :tag-limit="4"
        >
          <template #actions>
            <el-button
              v-if="!work.entry"
              size="small"
              text
              type="primary"
              @click.stop="quickAdd(work)"
            >
              + 想玩
            </el-button>
            <span v-else class="entry-hint">{{ entryStatusLabels[work.entry.status] }}</span>
          </template>
        </WorkCard>
      </div>

      <el-empty v-else-if="!loading" description="没有找到匹配的作品">
        <el-button @click="resetFilters">清除筛选</el-button>
      </el-empty>
    </div>

    <div v-if="total > limit" class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="limit"
        :total="total"
        layout="prev, pager, next, total"
        background
        @current-change="loadWorks"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Close, Search } from '@element-plus/icons-vue'
import WorkCard from '../components/WorkCard.vue'
import { api, entryStatusLabels } from '../api'
import { useCatalogStore } from '../store/game'
import type { NsfwPolicy, TagInfo, Work, WorkQuery } from '../types/api'

// 后端契约由另一个 agent 补齐（Work.title_zh、TagInfo.name_zh/aliases、
// WorkQuery 的 platform/language/min_year/max_length_minutes），这里用局部类型兜底，
// 保证类型文件更新前后都能编译。
type WorkWithZh = Work & { title_zh?: string | null }
type TagWithZh = TagInfo & { name_zh?: string | null; aliases?: string[] }

const route = useRoute()
const router = useRouter()
const store = useCatalogStore()

const HISTORY_KEY = 'gal-love:explore:search-history'

const platformOptions = [
  { value: 'win', label: 'Windows' },
  { value: 'swi', label: 'Switch' },
  { value: 'ps4', label: 'PS4' },
  { value: 'ps5', label: 'PS5' },
  { value: 'psv', label: 'PS Vita' },
  { value: 'and', label: 'Android' },
  { value: 'ios', label: 'iOS' },
  { value: 'web', label: 'Web' },
]
const languageOptions = [
  { value: 'zh-Hans', label: '简体中文' },
  { value: 'zh-Hant', label: '繁体中文' },
  { value: 'ja', label: '日语' },
  { value: 'en', label: '英语' },
]
const yearOptions = [2000, 2010, 2015, 2020, 2023]
const lengthOptions = [60, 180, 300, 600]

const searchInput = ref(String(route.query.q ?? ''))
const query = ref(searchInput.value)
const tag = ref(String(route.query.tag ?? ''))
const platform = ref(String(route.query.platform ?? ''))
const language = ref(String(route.query.language ?? ''))
const minYear = ref<number | undefined>(toNumber(route.query.min_year))
const maxLength = ref<number | undefined>(toNumber(route.query.max_length_minutes))
const sort = ref<NonNullable<WorkQuery['sort']>>(
  (route.query.sort as NonNullable<WorkQuery['sort']>) ?? 'rating',
)
const nsfwPolicy = ref<NsfwPolicy>('off')

const page = ref(1)
const limit = 24
const total = ref(0)
const works = ref<Work[]>([])
const tags = ref<TagInfo[]>([])
const loading = ref(false)

const suggestions = ref<Work[]>([])
const panelOpen = ref(false)
const history = ref<string[]>(loadHistory())

let debounceTimer: ReturnType<typeof setTimeout> | undefined
let blurTimer: ReturnType<typeof setTimeout> | undefined
let suppressInputWatch = false
let loadSeq = 0
let suggestSeq = 0

const hotTags = computed(() =>
  [...tags.value].sort((left, right) => right.work_count - left.work_count).slice(0, 8),
)

const displayWorks = computed(() =>
  works.value.map((work) => ({ ...work, title: displayTitle(work) })),
)

function toNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined
  const num = Number(value)
  return Number.isFinite(num) ? num : undefined
}

function displayTitle(work: Work): string {
  return (work as WorkWithZh).title_zh || work.title
}

function tagNameZh(item: TagInfo): string {
  return (item as TagWithZh).name_zh || item.name
}

// label 同时包含中文名、原名与别名，让 el-select 的 filterable 能按任意一种找到标签；
// 实际提交给后端的仍是原始 tag 名，保证与现有接口兼容。
function tagFilterLabel(item: TagInfo): string {
  const aliases = (item as TagWithZh).aliases ?? []
  return [tagNameZh(item), item.name, ...aliases].filter(Boolean).join(' ')
}

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((word): word is string => typeof word === 'string').slice(0, 8)
      : []
  } catch {
    return []
  }
}

function saveHistory(): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  } catch {
    // 隐私模式下 localStorage 不可写，忽略即可
  }
}

function pushHistory(word: string): void {
  if (!word) return
  history.value = [word, ...history.value.filter((item) => item !== word)].slice(0, 8)
  saveHistory()
}

function removeHistory(word: string): void {
  history.value = history.value.filter((item) => item !== word)
  saveHistory()
}

function clearHistory(): void {
  history.value = []
  saveHistory()
}

function setSearchInputSilently(value: string): void {
  suppressInputWatch = true
  searchInput.value = value
  suppressInputWatch = false
  if (debounceTimer) clearTimeout(debounceTimer)
}

function syncRoute(): void {
  const next: LocationQueryRaw = {}
  if (query.value.trim()) next.q = query.value.trim()
  if (tag.value) next.tag = tag.value
  if (platform.value) next.platform = platform.value
  if (language.value) next.language = language.value
  if (minYear.value) next.min_year = String(minYear.value)
  if (maxLength.value) next.max_length_minutes = String(maxLength.value)
  if (sort.value !== 'rating') next.sort = sort.value
  router.replace({ query: next })
}

function querySnapshot(): string {
  return [
    query.value,
    tag.value,
    platform.value,
    language.value,
    minYear.value ?? '',
    maxLength.value ?? '',
    sort.value,
  ].join('|')
}

function readRouteQuery(): void {
  const q = route.query
  setSearchInputSilently(String(q.q ?? ''))
  query.value = searchInput.value
  tag.value = String(q.tag ?? '')
  platform.value = String(q.platform ?? '')
  language.value = String(q.language ?? '')
  minYear.value = toNumber(q.min_year)
  maxLength.value = toNumber(q.max_length_minutes)
  sort.value = (q.sort as NonNullable<WorkQuery['sort']>) ?? 'rating'
  suggestions.value = []
}

async function loadWorks(): Promise<void> {
  const current = ++loadSeq
  // 断言为 WorkQuery 以绕过尚未更新的类型定义；多出的字段会被原样发给后端。
  const params = {
    q: query.value.trim() || undefined,
    tag: tag.value || undefined,
    platform: platform.value || undefined,
    language: language.value || undefined,
    min_year: minYear.value || undefined,
    max_length_minutes: maxLength.value || undefined,
    sort: sort.value,
    page: page.value,
    limit,
    nsfw_policy: nsfwPolicy.value,
  } as WorkQuery

  loading.value = true
  try {
    const data = await api.works(params)
    if (current !== loadSeq) return
    works.value = data.items
    total.value = data.total
  } catch (error) {
    if (current !== loadSeq) return
    ElMessage.error(error instanceof Error ? error.message : '加载作品失败')
  } finally {
    if (current === loadSeq) loading.value = false
  }
}

async function fetchSuggestions(word: string): Promise<void> {
  if (!word) {
    suggestions.value = []
    return
  }
  const current = ++suggestSeq
  try {
    const data = await api.works({ q: word, limit: 6 })
    if (current !== suggestSeq) return
    suggestions.value = data.items
  } catch {
    if (current === suggestSeq) suggestions.value = []
  }
}

// 真正发起搜索（防抖结束 / 回车 / 点击候选）。recordHistory 控制是否写入历史。
function performSearch(recordHistory: boolean): void {
  if (recordHistory) pushHistory(query.value)
  page.value = 1
  syncRoute()
  void loadWorks()
}

function commitNow(text?: string): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  suppressInputWatch = true
  if (text !== undefined) searchInput.value = text
  query.value = searchInput.value.trim()
  suppressInputWatch = false
  suggestions.value = []
  panelOpen.value = false
  performSearch(true)
}

function onFilterChange(): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  query.value = searchInput.value.trim()
  performSearch(false)
}

function onEnter(): void {
  commitNow()
}

function onClear(): void {
  commitNow('')
}

function onSearchBlur(): void {
  if (blurTimer) clearTimeout(blurTimer)
  blurTimer = setTimeout(() => {
    panelOpen.value = false
  }, 160)
}

function chooseSuggestion(work: Work): void {
  commitNow(displayTitle(work))
}

function chooseHistory(word: string): void {
  commitNow(word)
}

function chooseTag(item: TagInfo): void {
  tag.value = item.name
  panelOpen.value = false
  onFilterChange()
}

function resetFilters(): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  setSearchInputSilently('')
  query.value = ''
  tag.value = ''
  platform.value = ''
  language.value = ''
  minYear.value = undefined
  maxLength.value = undefined
  sort.value = 'rating'
  nsfwPolicy.value = store.settings.nsfw_policy ?? 'off'
  suggestions.value = []
  panelOpen.value = false
  performSearch(false)
}

async function quickAdd(work: Work): Promise<void> {
  try {
    await store.saveEntry(work.id, { status: 'want' })
    const entry = store.entryFor(work.id)
    const original = works.value.find((item) => item.id === work.id)
    if (original) original.entry = entry
    work.entry = entry
    ElMessage.success(`已把《${displayTitle(work)}》加入想玩`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  }
}

// 输入防抖：300ms 后提交查询、刷新候选并重新拉取列表。
watch(
  searchInput,
  (value) => {
    if (suppressInputWatch) return
    if (debounceTimer) clearTimeout(debounceTimer)
    if (!value.trim()) suggestions.value = []
    debounceTimer = setTimeout(() => {
      query.value = value.trim()
      pushHistory(query.value)
      page.value = 1
      syncRoute()
      void loadWorks()
      void fetchSuggestions(query.value)
    }, 300)
  },
  { flush: 'sync' },
)

// 浏览器前进/后退或外部修改 URL 时同步回表单状态。
watch(
  () => route.query,
  () => {
    const before = querySnapshot()
    readRouteQuery()
    if (before !== querySnapshot()) {
      page.value = 1
      void loadWorks()
    }
  },
)

onMounted(async () => {
  await store.fetchSettings()
  nsfwPolicy.value = store.settings.nsfw_policy ?? 'off'
  try {
    tags.value = (await api.tags({ limit: 300 })).items
  } catch {
    tags.value = []
  }
  await loadWorks()
})
</script>

<style scoped>
.explore {
  max-width: 1180px;
  margin: 0 auto;
  padding: 36px 28px 56px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 22px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.page-head h1 {
  margin: 8px 0 6px;
  font-size: 30px;
  letter-spacing: -0.01em;
}

.page-head p {
  margin: 0;
  color: #8a8fa3;
  font-size: 14px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  margin-bottom: 24px;
}

.search-wrap {
  position: relative;
  width: 300px;
}

.search {
  width: 100%;
}

.filter-select {
  width: 150px;
}

.tag-select {
  width: 210px;
}

.sort-select {
  width: 140px;
}

.option-alias {
  margin-left: 6px;
  color: #9a8fd0;
  font-size: 12px;
}

.option-count {
  float: right;
  color: #8a8fa3;
  font-size: 12px;
}

.switch-field {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #5b5478;
}

.search-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  max-height: 360px;
  overflow: auto;
  padding: 8px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(31, 35, 64, 0.1);
  box-shadow: 0 12px 32px rgba(60, 45, 120, 0.16);
}

.panel-section + .panel-section {
  border-top: 1px solid rgba(31, 35, 64, 0.06);
  margin-top: 6px;
  padding-top: 8px;
}

.panel-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px 6px;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #9a8fd0;
}

.link-btn {
  border: 0;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #6f57d9;
  cursor: pointer;
}

.panel-row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 0;
  background: none;
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
  color: #2e2a40;
  text-align: left;
  cursor: pointer;
}

.panel-row:hover {
  background: #f1eefd;
}

.row-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-meta {
  flex-shrink: 0;
  font-size: 12px;
  color: #8a8fa3;
}

.panel-empty {
  padding: 10px 8px;
  font-size: 13px;
  color: #8a8fa3;
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 6px 6px;
}

.history-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #f1eefd;
  color: #5a44c4;
  font-size: 12px;
  cursor: pointer;
}

.chip-close {
  font-size: 11px;
  opacity: 0.6;
}

.hot-tag {
  cursor: pointer;
}

.results {
  min-height: 240px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 18px;
}

.entry-hint {
  display: inline-block;
  font-size: 12px;
  color: #67a35b;
  padding: 4px 0;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

@media (max-width: 720px) {
  .explore {
    padding: 24px 16px 40px;
  }

  .search-wrap,
  .filter-select,
  .tag-select,
  .sort-select {
    width: 100%;
  }

  .search-panel {
    max-height: 280px;
  }
}
</style>
