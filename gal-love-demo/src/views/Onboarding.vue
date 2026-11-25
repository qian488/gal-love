<template>
  <div class="onboarding-page">
    <div class="onboarding-shell">
      <header class="topbar">
        <div class="brand">
          <span class="brand-mark">G</span>
          <span>代号G</span>
        </div>
        <el-button text type="primary" @click="skip">跳过引导</el-button>
      </header>

      <div class="progress-head">
        <div class="progress-meta">
          <span>第 {{ step + 1 }} / {{ stepMeta.length }} 步 · {{ stepMeta[step].label }}</span>
          <span>{{ progress }}%</span>
        </div>
        <el-progress :percentage="progress" :stroke-width="8" :show-text="false" />
        <h1>{{ stepMeta[step].title }}</h1>
        <p v-if="stepMeta[step].desc">{{ stepMeta[step].desc }}</p>
      </div>

      <!-- 第 1 步：欢迎 -->
      <section v-if="step === 0" class="step-panel welcome">
        <div class="welcome-visual" aria-hidden="true">
          <span class="spark spark-a" />
          <span class="spark spark-b" />
          <span class="spark spark-c" />
          <div class="welcome-card">
            <span>今日推荐</span>
            <strong>懂你的下一部</strong>
            <small>从你喜欢的故事出发</small>
          </div>
        </div>
        <ol class="welcome-list">
          <li><span>01</span> 从候选中挑出 3–5 部喜欢的作品</li>
          <li><span>02</span> 挑好后自动记入游戏库</li>
          <li><span>03</span> 立即获得贴合口味的推荐</li>
        </ol>
        <div class="step-footer center">
          <el-button type="primary" round size="large" @click="start">开始挑选</el-button>
          <el-button text @click="skip">先随便看看</el-button>
        </div>
      </section>

      <!-- 第 2 步：挑选作品 -->
      <section v-else-if="step === 1" class="step-panel select">
        <div class="pick-toolbar">
          <span class="pick-tip">选 {{ minPicks }}–{{ maxPicks }} 部你喜欢的</span>
          <el-button text size="small" :loading="loadingWorks" @click="loadCandidates()">
            换一批 <el-icon><Refresh /></el-icon>
          </el-button>
        </div>

        <div v-loading="loadingWorks" class="work-grid">
          <div
            v-for="work in candidates"
            :key="work.id"
            class="pick-card"
            :class="{ selected: isSelected(work.id) }"
            role="button"
            tabindex="0"
            :aria-pressed="isSelected(work.id)"
            @click="toggle(work.id)"
            @keydown.enter.prevent="toggle(work.id)"
            @keydown.space.prevent="toggle(work.id)"
          >
            <div class="pick-cover">
              <img
                v-if="work.cover_url && !brokenImages.includes(work.id)"
                :src="work.cover_url"
                :alt="work.title"
                loading="lazy"
                referrerpolicy="no-referrer"
                @error="brokenImages.push(work.id)"
              />
              <div v-else class="cover-placeholder">{{ work.title.slice(0, 1) }}</div>
              <span class="pick-check" :class="{ on: isSelected(work.id) }">
                {{ isSelected(work.id) ? '✓' : '' }}
              </span>
            </div>
            <div class="pick-body">
              <h3 :title="work.title">{{ work.title }}</h3>
              <p class="pick-meta">{{ metaText(work) }}</p>
              <span class="pick-state">{{ isSelected(work.id) ? '已选择' : '点击选择' }}</span>
            </div>
          </div>
        </div>

        <el-empty
          v-if="!loadingWorks && !candidates.length"
          description="暂时没有候选作品，可以跳过引导后再到探索页记录"
        />

        <div class="step-footer">
          <span class="count-hint" :class="{ warn: selectedIds.length < minPicks }">
            已选 {{ selectedIds.length }} / {{ maxPicks }}（至少 {{ minPicks }} 部）
          </span>
          <div class="footer-actions">
            <el-button @click="step = 0">上一步</el-button>
            <el-button
              type="primary"
              :disabled="selectedIds.length < minPicks"
              :loading="saving"
              @click="finish"
            >
              完成引导
            </el-button>
          </div>
        </div>
      </section>

      <!-- 第 3 步：完成 -->
      <section v-else class="step-panel done">
        <div class="done-badge">✓</div>
        <p class="done-summary">
          已记录 <strong>{{ successCount }}</strong> 部作品，口味画像已建立。
        </p>
        <p v-if="failedTitles.length" class="done-failed">
          以下作品保存失败，可在游戏库中手动补记：{{ failedTitles.join('、') }}
        </p>
        <div class="step-footer center">
          <el-button type="primary" round size="large" @click="goHome">进入首页查看推荐</el-button>
          <span v-if="!failedTitles.length" class="auto-hint">稍后会自动返回首页</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import type { Work } from '../types/api'

const STORAGE_KEY = 'gal-love-onboard-v1'
const minPicks = 3
const maxPicks = 5

const stepMeta = [
  {
    label: '欢迎',
    title: '欢迎来到代号G',
    desc: '',
  },
  {
    label: '挑选作品',
    title: '选出你喜欢的作品',
    desc: '',
  },
  {
    label: '完成',
    title: '口味画像已建立',
    desc: '',
  },
]

const router = useRouter()
const step = ref(0)
const progress = computed(() => Math.round(((step.value + 1) / stepMeta.length) * 100))

const candidates = ref<Work[]>([])
const loadingWorks = ref(false)
const selectedIds = ref<number[]>([])
const brokenImages = ref<number[]>([])
const saving = ref(false)
const successCount = ref(0)
const failedTitles = ref<string[]>([])

let jumpTimer: ReturnType<typeof setTimeout> | null = null

function markDone() {
  try {
    localStorage.setItem(STORAGE_KEY, 'done')
  } catch {
    // 隐私模式等场景下写入失败时，仍允许继续流程
  }
}

function goHome(message?: string) {
  markDone()
  if (message) ElMessage.success(message)
  router.push('/')
}

function skip() {
  goHome('已跳过引导，随时可以在游戏库中记录作品')
}

function start() {
  step.value = 1
}

function isSelected(id: number) {
  return selectedIds.value.includes(id)
}

function toggle(id: number) {
  const index = selectedIds.value.indexOf(id)
  if (index >= 0) {
    selectedIds.value.splice(index, 1)
    return
  }
  if (selectedIds.value.length >= maxPicks) {
    ElMessage.warning(`最多选择 ${maxPicks} 部作品`)
    return
  }
  selectedIds.value.push(id)
}

function metaText(work: Work): string {
  const parts: string[] = []
  if (work.release_year) parts.push(String(work.release_year))
  if (work.companies.length) parts.push(work.companies[0])
  if (work.length_minutes) {
    const hours = Math.round(work.length_minutes / 60)
    parts.push(hours >= 1 ? `约 ${hours} 小时` : `${work.length_minutes} 分钟`)
  }
  return parts.join(' · ')
}

async function loadCandidates() {
  loadingWorks.value = true
  try {
    const data = await api.works({ sort: 'random', limit: 30, include_nsfw: false })
    candidates.value = data.items
  } catch (error) {
    candidates.value = []
    ElMessage.error(error instanceof Error ? error.message : '候选作品加载失败')
  } finally {
    loadingWorks.value = false
  }
}

async function finish() {
  if (selectedIds.value.length < minPicks || saving.value) return
  saving.value = true
  successCount.value = 0
  failedTitles.value = []

  const picked = candidates.value.filter((work) => selectedIds.value.includes(work.id))
  try {
    for (const work of picked) {
      try {
        await api.saveEntry(work.id, { rating: 9, favorite: true, status: 'finished' })
        successCount.value += 1
      } catch (error) {
        failedTitles.value.push(work.title)
        ElMessage.error(
          `《${work.title}》保存失败：${error instanceof Error ? error.message : '请稍后重试'}`,
        )
      }
    }

    markDone()
    step.value = 2
    if (!failedTitles.value.length) {
      ElMessage.success(`已记录 ${successCount.value} 部作品，正在生成你的口味画像`)
    }
  } finally {
    saving.value = false
  }
}

watch(step, (value) => {
  // 全部保存成功时短暂停留后自动回首页；有失败项则留在本页让用户确认。
  if (value === 2 && !failedTitles.value.length) {
    jumpTimer = setTimeout(() => router.push('/'), 2400)
  }
})

onMounted(loadCandidates)

onBeforeUnmount(() => {
  if (jumpTimer) clearTimeout(jumpTimer)
})
</script>

<style scoped>
.onboarding-page {
  min-height: 100vh;
  padding: 32px 20px 64px;
  background:
    radial-gradient(circle at 12% 8%, rgba(151, 122, 255, 0.22), transparent 42%),
    radial-gradient(circle at 88% 18%, rgba(226, 141, 200, 0.16), transparent 38%),
    #f7f5fd;
}

.onboarding-shell {
  max-width: 860px;
  margin: 0 auto;
  background: #fff;
  border-radius: 24px;
  border: 1px solid rgba(78, 56, 144, 0.08);
  box-shadow: 0 24px 70px rgba(53, 36, 105, 0.12);
  padding: 24px 32px 36px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 18px;
  border-bottom: 1px solid #f0edfa;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #382e63;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  color: #fff;
  font-size: 18px;
  background: linear-gradient(135deg, #7b5cff, #b06ae0);
}

.progress-head {
  padding: 26px 0 6px;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #8a80ae;
  margin-bottom: 10px;
}

.progress-head h1 {
  margin: 20px 0 8px;
  font-size: clamp(24px, 4vw, 32px);
  color: #2f274a;
}

.progress-head p {
  margin: 0;
  color: #7f7996;
  font-size: 14px;
  line-height: 1.8;
}

.step-panel {
  padding-top: 18px;
}

.welcome-visual {
  position: relative;
  min-height: 190px;
  border-radius: 18px;
  background: linear-gradient(135deg, #2c2350, #4b2f72 60%, #6a3c84);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spark {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
}

.spark-a {
  width: 150px;
  height: 150px;
  background: rgba(255, 190, 226, 0.45);
  top: -30px;
  left: 8%;
}

.spark-b {
  width: 110px;
  height: 110px;
  background: rgba(150, 120, 255, 0.5);
  bottom: -20px;
  right: 12%;
}

.spark-c {
  width: 70px;
  height: 70px;
  background: rgba(150, 215, 255, 0.35);
  top: 20px;
  right: 30%;
}

.welcome-card {
  position: relative;
  z-index: 1;
  min-width: 220px;
  padding: 20px 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(14px);
  color: #fff;
  display: grid;
  gap: 8px;
}

.welcome-card span {
  font-size: 11px;
  letter-spacing: 0.16em;
  color: rgba(255, 255, 255, 0.7);
}

.welcome-card strong {
  font-size: 22px;
}

.welcome-card small {
  color: rgba(255, 255, 255, 0.75);
}

.welcome-list {
  margin: 24px 0 8px;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.welcome-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #5f5878;
}

.welcome-list span {
  color: #8a6cff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.pick-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.pick-tip {
  font-size: 13px;
  color: #7f7996;
}

.work-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
  min-height: 120px;
}

.pick-card {
  border: 2px solid transparent;
  border-radius: 14px;
  background: #fff;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  box-shadow: 0 8px 22px rgba(50, 36, 96, 0.08);
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
  outline: none;
}

.pick-card:hover {
  transform: translateY(-3px);
}

.pick-card:focus-visible {
  border-color: #9f86ff;
}

.pick-card.selected {
  border-color: #7b5cff;
  box-shadow: 0 12px 28px rgba(123, 92, 255, 0.24);
}

.pick-cover {
  position: relative;
  aspect-ratio: 3 / 4;
  background: linear-gradient(135deg, #e4ddff, #f6e9ff);
}

.pick-cover img,
.cover-placeholder {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-placeholder {
  font-size: 2.5rem;
  font-weight: 700;
  color: rgba(88, 64, 180, 0.5);
}

.pick-check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: rgba(30, 24, 50, 0.35);
  color: #fff;
  font-size: 13px;
  line-height: 18px;
  text-align: center;
}

.pick-check.on {
  background: #7b5cff;
  border-color: #7b5cff;
}

.pick-body {
  padding: 10px 12px 12px;
}

.pick-body h3 {
  margin: 0 0 4px;
  font-size: 14px;
  line-height: 1.4;
  color: #322b4a;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pick-meta {
  margin: 0 0 8px;
  font-size: 11px;
  color: #9993aa;
  min-height: 15px;
}

.pick-state {
  font-size: 12px;
  color: #7b5cff;
}

.pick-card.selected .pick-state {
  font-weight: 700;
}

.step-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #f0edfa;
}

.step-footer.center {
  justify-content: center;
  flex-wrap: wrap;
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.count-hint {
  font-size: 13px;
  color: #7f7996;
}

.count-hint.warn {
  color: #c07a3e;
}

.done {
  text-align: center;
  padding: 26px 0 8px;
}

.done-badge {
  width: 64px;
  height: 64px;
  margin: 0 auto 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7b5cff, #b06ae0);
  color: #fff;
  font-size: 32px;
  line-height: 64px;
  box-shadow: 0 12px 30px rgba(123, 92, 255, 0.3);
}

.done-summary {
  font-size: 15px;
  color: #5f5878;
}

.done-summary strong {
  color: #7b5cff;
  font-size: 20px;
}

.done-failed {
  font-size: 13px;
  color: #c07a3e;
  line-height: 1.7;
}

.auto-hint {
  font-size: 12px;
  color: #a29ab8;
}

@media (max-width: 640px) {
  .onboarding-page {
    padding: 12px 10px 36px;
  }

  .onboarding-shell {
    padding: 18px 16px 26px;
    border-radius: 18px;
  }

  .work-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .step-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .footer-actions {
    justify-content: space-between;
  }

  .footer-actions .el-button {
    flex: 1;
    margin-left: 0;
  }
}
</style>
