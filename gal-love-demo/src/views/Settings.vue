<template>
  <div class="settings">
    <header class="page-head">
      <div>
        <span class="eyebrow">PREFERENCES</span>
        <h1>设置与数据</h1>
        <p>调整推荐偏好、管理数据与作品。</p>
      </div>
      <el-tag round effect="plain">{{ store.algorithmVersion }}</el-tag>
    </header>

    <div class="stats-row">
      <div class="mini-stat"><strong>{{ store.stats?.works ?? '—' }}</strong><span>作品</span></div>
      <div class="mini-stat"><strong>{{ store.stats?.tags ?? '—' }}</strong><span>标签</span></div>
      <div class="mini-stat"><strong>{{ store.stats?.entries ?? '—' }}</strong><span>游戏库记录</span></div>
      <div class="mini-stat"><strong>{{ store.stats?.sync_runs ?? '—' }}</strong><span>同步任务</span></div>
    </div>

    <div class="columns">
      <section class="panel">
        <div class="panel-head">
          <h2>推荐偏好</h2>
          <el-button text type="primary" @click="resetForm">恢复当前设置</el-button>
        </div>

        <el-form label-width="110px" label-position="left">
          <el-form-item label="内容范围">
            <el-select v-model="form.nsfw_policy" style="width: 240px">
              <el-option label="仅全年龄" value="off" />
              <el-option label="含成人剧情作" value="story" />
              <el-option label="全部内容" value="all" />
            </el-select>
          </el-form-item>

          <el-form-item label="参与来源">
            <div class="switch-row">
              <el-select
                v-model="form.home_profile_sources"
                multiple
                collapse-tags
                placeholder="不选则全部参与"
                style="width: 320px"
              >
                <el-option label="我的游戏库" value="library" />
                <el-option
                  v-for="item in personaOptions"
                  :key="item.key"
                  :label="item.title"
                  :value="item.key"
                />
              </el-select>
              <span class="switch-hint">只选游戏库时，首页只用游戏库画像</span>
            </div>
          </el-form-item>

          <el-form-item label="最早年份">
            <el-input-number
              v-model="form.min_year"
              :min="1900"
              :max="2100"
              controls-position="right"
              placeholder="不限"
            />
          </el-form-item>

          <el-form-item label="最长时长（分钟）">
            <el-input-number
              v-model="form.max_length_minutes"
              :min="30"
              :max="30000"
              :step="30"
              controls-position="right"
              placeholder="不限"
            />
          </el-form-item>

          <el-form-item label="平台">
            <el-select v-model="form.platform" clearable placeholder="不限平台" style="width: 220px">
              <el-option label="Windows" value="win" />
              <el-option label="Nintendo Switch" value="swi" />
              <el-option label="PlayStation 4" value="ps4" />
              <el-option label="PlayStation 5" value="ps5" />
              <el-option label="PS Vita" value="psv" />
              <el-option label="Android" value="and" />
              <el-option label="iOS" value="ios" />
              <el-option label="Web" value="web" />
            </el-select>
          </el-form-item>

          <el-form-item label="语言">
            <el-select v-model="form.language" clearable placeholder="不限语言" style="width: 220px">
              <el-option label="简体中文" value="zh-Hans" />
              <el-option label="繁體中文" value="zh-Hant" />
              <el-option label="日本語" value="ja" />
              <el-option label="English" value="en" />
            </el-select>
          </el-form-item>

          <el-form-item label="多样性">
            <el-slider
              v-model="form.diversity"
              :min="0"
              :max="0.5"
              :step="0.05"
              show-input
              :show-input-controls="false"
              class="diversity-slider"
            />
          </el-form-item>
        </el-form>

        <div class="panel-actions">
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </div>
      </section>

      <section class="panel">
        <h2>数据导入</h2>
        <p class="panel-desc">从 VNDB / Bangumi 导入作品。</p>

        <div class="import-block">
          <div class="import-head">
            <h3>VNDB</h3>
            <el-tag size="small" effect="plain">主数据源</el-tag>
          </div>
          <div class="import-fields">
            <el-input-number v-model="vndbLimit" :min="1" :max="5000" :step="20" />
            <span>部作品</span>
            <el-input-number v-model="vndbMinVotes" :min="0" :max="10000" :step="10" />
            <span>最少投票数</span>
          </div>
          <div class="import-fields">
            <el-switch v-model="vndbIncremental" />
            <span>增量导入</span>
          </div>
          <el-button type="primary" :loading="importing === 'vndb'" @click="runVndb">
            导入 VNDB
          </el-button>
        </div>

        <el-divider />

        <div class="import-block">
          <div class="import-head">
            <h3>Bangumi</h3>
            <el-tag size="small" effect="plain">中文补充</el-tag>
          </div>
          <div class="import-fields">
            <el-input-number v-model="bangumiLimit" :min="1" :max="2000" :step="20" />
            <span>条游戏条目</span>
          </div>
          <div class="import-fields">
            <el-switch v-model="bangumiIncremental" />
            <span>增量导入</span>
          </div>
          <el-button :loading="importing === 'bangumi'" @click="runBangumi">
            导入 Bangumi
          </el-button>
        </div>

        <el-divider />

        <el-button text type="primary" @click="manualVisible = true">
          <el-icon><EditPen /></el-icon> 手工录入作品
        </el-button>
      </section>
    </div>

    <section class="panel sync-panel">
      <div class="panel-head">
        <div>
          <h2>同步记录</h2>
        </div>
        <el-button text type="primary" :loading="runsLoading" @click="refreshRuns">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>

      <el-table :data="runs" size="small" empty-text="还没有同步任务">
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column prop="source" label="来源" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'"
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="统计" min-width="240">
          <template #default="{ row }">{{ runSummary(row) }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="错误" min-width="160">
          <template #default="{ row }">
            <span class="error-text">{{ row.error || '' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="section-title">
      <span class="eyebrow">DATA TOOLS</span>
      <h2>数据治理与维护</h2>
    </div>

    <div class="tool-panels">
      <DuplicatesPanel @merged="refreshStats" />
      <BackupPanel @changed="refreshStats" />
      <VotesPanel />
    </div>

    <el-dialog v-model="manualVisible" title="手工录入作品" width="min(560px, 92vw)">
      <el-form label-width="84px" label-position="left">
        <el-form-item label="标题" required>
          <el-input v-model="manual.title" placeholder="作品标题" />
        </el-form-item>
        <el-form-item label="中文标题">
          <el-input v-model="manual.title_zh" placeholder="可选" />
        </el-form-item>
        <el-form-item label="原名">
          <el-input v-model="manual.original_title" placeholder="可选" />
        </el-form-item>
        <el-form-item label="发售日期">
          <el-input v-model="manual.release_date" placeholder="YYYY-MM-DD 或 YYYY" />
        </el-form-item>
        <el-form-item label="我的评分">
          <el-input-number v-model="manual.rating" :min="0" :max="10" :step="0.5" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="manual.tags" placeholder="用逗号分隔，例如：悬疑, 推理, 剧情" />
        </el-form-item>
        <el-form-item label="开发商">
          <el-input v-model="manual.companies" placeholder="用逗号分隔" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="manual.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="NSFW">
          <el-switch v-model="manual.nsfw" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createManual">保存作品</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import { useCatalogStore } from '../store/game'
import BackupPanel from '../components/BackupPanel.vue'
import DuplicatesPanel from '../components/DuplicatesPanel.vue'
import VotesPanel from '../components/VotesPanel.vue'
import type { NsfwPolicy, PersonaProviderInfo, Settings, SyncRun } from '../types/api'

const store = useCatalogStore()

const saving = ref(false)
const importing = ref<'' | 'vndb' | 'bangumi'>('')
const runsLoading = ref(false)
const runs = ref<SyncRun[]>([])

const vndbLimit = ref(100)
const vndbMinVotes = ref(50)
const vndbIncremental = ref(true)
const bangumiLimit = ref(100)
const bangumiIncremental = ref(true)

const manualVisible = ref(false)
const creating = ref(false)
const manual = reactive({
  title: '',
  title_zh: '',
  original_title: '',
  release_date: '',
  rating: undefined as number | undefined,
  tags: '',
  companies: '',
  description: '',
  nsfw: false,
})

const form = reactive({
  nsfw_policy: 'off' as NsfwPolicy,
  home_profile_sources: [] as string[],
  min_year: undefined as number | undefined,
  max_length_minutes: undefined as number | undefined,
  platform: '',
  language: '',
  diversity: 0.15,
})

const personaOptions = ref<PersonaProviderInfo[]>([])

function applySettings(settings: Settings) {
  form.nsfw_policy = settings.nsfw_policy ?? (settings.include_nsfw ? 'all' : 'off')
  form.home_profile_sources = settings.home_profile_sources ?? []
  form.min_year = settings.min_year ?? undefined
  form.max_length_minutes = settings.max_length_minutes ?? undefined
  form.platform = settings.platform ?? ''
  form.language = settings.language ?? ''
  form.diversity = settings.diversity
}

async function save() {
  saving.value = true
  try {
    await store.saveSettings({
      nsfw_policy: form.nsfw_policy,
      home_profile_sources: form.home_profile_sources.length
        ? form.home_profile_sources
        : null,
      min_year: form.min_year ?? null,
      max_length_minutes: form.max_length_minutes ?? null,
      platform: form.platform || null,
      language: form.language || null,
      diversity: form.diversity,
    })
    ElMessage.success('设置已保存，推荐会按新设置重新计算')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function resetForm() {
  applySettings(store.settings)
}

async function runVndb() {
  importing.value = 'vndb'
  try {
    const result = await api.importVndb({
      limit: vndbLimit.value,
      min_votes: vndbMinVotes.value,
      wait: false,
      incremental: vndbIncremental.value,
    })
    ElMessage.success(`VNDB 导入任务 #${result.run_id} 已开始`)
    window.setTimeout(refreshRuns, 1500)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    importing.value = ''
  }
}

async function runBangumi() {
  importing.value = 'bangumi'
  try {
    const result = await api.importBangumi({
      limit: bangumiLimit.value,
      avg_only: true,
      wait: false,
      incremental: bangumiIncremental.value,
    })
    ElMessage.success(`Bangumi 导入任务 #${result.run_id} 已开始`)
    window.setTimeout(refreshRuns, 1500)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    importing.value = ''
  }
}

async function refreshRuns() {
  runsLoading.value = true
  try {
    runs.value = (await api.syncRuns(10)).items
    await store.loadStats()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载同步记录失败')
  } finally {
    runsLoading.value = false
  }
}

async function refreshStats() {
  await store.loadStats()
}

function splitList(value: string): string[] {
  return value
    .split(/[,，、\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function createManual() {
  if (!manual.title.trim()) {
    ElMessage.warning('请填写作品标题')
    return
  }
  creating.value = true
  try {
    await api.createWork({
      title: manual.title.trim(),
      title_zh: manual.title_zh.trim() || null,
      original_title: manual.original_title.trim() || null,
      release_date: manual.release_date.trim() || null,
      rating: manual.rating ?? null,
      tags: splitList(manual.tags),
      companies: splitList(manual.companies),
      description: manual.description.trim() || null,
      nsfw: manual.nsfw,
    })
    ElMessage.success('作品已创建')
    manualVisible.value = false
    manual.title = ''
    manual.title_zh = ''
    manual.original_title = ''
    manual.release_date = ''
    manual.rating = undefined
    manual.tags = ''
    manual.companies = ''
    manual.description = ''
    manual.nsfw = false
    await store.loadStats()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建失败')
  } finally {
    creating.value = false
  }
}

function runSummary(run: SyncRun): string {
  const labels: Record<string, string> = {
    requested: '请求',
    fetched: '抓取',
    imported: '入库',
    skipped: '跳过',
    failed: '失败',
  }
  const parts: string[] = []
  for (const key of Object.keys(labels)) {
    const value = run.stats?.[key]
    if (typeof value === 'number') parts.push(`${labels[key]} ${value}`)
  }
  return parts.join(' · ') || '—'
}

function formatTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  await store.fetchSettings()
  applySettings(store.settings)
  api.personaProviders()
    .then((data) => {
      personaOptions.value = data.items.filter((item) => item.key !== 'tarot')
    })
    .catch(() => {
      personaOptions.value = []
    })
  await store.loadStats()
  await refreshRuns()
})
</script>

<style scoped>
.settings {
  max-width: 1120px;
  margin: 0 auto;
  padding: 36px 28px 56px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.page-head h1 {
  margin: 8px 0 6px;
  font-size: 30px;
}

.page-head p {
  margin: 0;
  color: #8a8fa3;
  font-size: 14px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.mini-stat {
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(31, 35, 64, 0.06);
}

.mini-stat strong {
  display: block;
  font-size: 22px;
  color: #362e5c;
}

.mini-stat span {
  font-size: 12px;
  color: #8a8fa3;
}

.columns {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 18px;
  align-items: start;
}

.panel {
  background: #fff;
  border-radius: 16px;
  padding: 22px;
  border: 1px solid rgba(31, 35, 64, 0.06);
}

.panel h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-desc {
  margin: 0 0 16px;
  color: #8a8fa3;
  font-size: 13px;
  line-height: 1.7;
}

.switch-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.switch-hint {
  font-size: 12px;
  color: #9a9fb0;
}

.diversity-slider {
  width: 100%;
  margin-right: 12px;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.import-block {
  padding: 4px 0;
}

.import-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.import-head h3 {
  margin: 0;
  font-size: 16px;
}

.import-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #8a8fa3;
}

.import-block small {
  display: block;
  margin-top: 8px;
  color: #9a9fb0;
  line-height: 1.7;
}

.sync-panel {
  margin-top: 18px;
}

.section-title {
  margin: 28px 0 14px;
}

.section-title h2 {
  margin: 6px 0 0;
  font-size: 22px;
}

.tool-panels {
  display: grid;
  gap: 18px;
}

.error-text {
  color: #c45656;
  font-size: 12px;
}

@media (max-width: 900px) {
  .columns {
    grid-template-columns: 1fr;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .settings {
    padding: 24px 16px 40px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
