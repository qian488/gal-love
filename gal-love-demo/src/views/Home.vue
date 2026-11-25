<template>
  <div class="home">
    <transition name="intro-fade">
      <div v-if="showIntroBar" class="intro-bar">
        <div class="intro-bar-inner">
          <el-icon class="intro-icon"><MagicStick /></el-icon>
          <span class="intro-text">
            <strong>挑 3–5 部喜欢的作品</strong>，开始获得推荐
          </span>
          <div class="intro-actions">
            <el-button type="primary" size="small" round @click="router.push('/onboarding')">
              开始引导
            </el-button>
            <el-button text size="small" @click="dismissIntroBar">不再提示</el-button>
          </div>
        </div>
      </div>
    </transition>

    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <h1>下一部，玩什么？</h1>
          <div class="search-row">
            <el-input
              v-model="search"
              size="large"
              placeholder="搜索作品、别名或简介…"
              clearable
              @keyup.enter="openSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="large" type="primary" @click="openSearch">去探索</el-button>
          </div>
        </div>
      </div>
    </section>

    <section class="layout">
      <main class="main-column">
        <div class="section-head">
          <h2>为你推荐</h2>
        </div>

        <div v-loading="store.loadingRecommendations" class="recommendation-list">
          <WorkCard
            v-for="work in store.recommendations"
            :key="work.id"
            :work="work"
            reason
          >
            <template #actions>
              <div class="card-actions" @click.stop>
                <el-button
                  size="small"
                  :loading="addingId === work.id"
                  @click="quickWant(work)"
                >
                  想玩
                </el-button>
                <el-button size="small" type="primary" plain @click="openEntry(work)">
                  记录
                </el-button>
                <el-button size="small" text @click="notInterested(work)">
                  不感兴趣
                </el-button>
              </div>
            </template>
          </WorkCard>
        </div>

        <el-empty
          v-if="!store.loadingRecommendations && !store.recommendations.length"
          description="还没有可推荐的作品"
        >
          <el-button type="primary" @click="router.push('/onboarding')">
            开始冷启动引导
          </el-button>
          <el-button @click="router.push('/explore')">自己去探索</el-button>
        </el-empty>

        <div class="section-head secondary">
          <h2>继续探索</h2>
          <el-button text type="primary" @click="router.push('/explore')">
            全部作品 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>

        <div class="explore-strip">
          <div v-for="tip in tips" :key="tip.title" class="tip-card">
            <h3>{{ tip.title }}</h3>
            <el-button text type="primary" @click="router.push(tip.to)">
              {{ tip.action }} <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
      </main>

      <aside class="side-column">
        <section class="panel profile-panel">
          <div class="panel-head">
            <h2>我的口味</h2>
            <el-button text type="primary" @click="router.push('/library')">游戏库</el-button>
          </div>

          <div class="status-grid">
            <div class="status-cell">
              <strong>{{ counts.finished }}</strong>
              <span>玩过</span>
            </div>
            <div class="status-cell">
              <strong>{{ counts.playing }}</strong>
              <span>在玩</span>
            </div>
            <div class="status-cell">
              <strong>{{ counts.want }}</strong>
              <span>想玩</span>
            </div>
            <div class="status-cell">
              <strong>{{ counts.dropped }}</strong>
              <span>弃坑</span>
            </div>
          </div>

          <template v-if="store.hasProfile">
            <h3 class="sub-title">偏爱的题材</h3>
            <div class="taste-tags">
              <el-tag
                v-for="tag in store.tasteTags"
                :key="tag.name"
                round
                effect="light"
              >
                {{ tag.name }}
              </el-tag>
              <span v-if="!store.tasteTags.length" class="muted">暂无</span>
            </div>
          </template>

          <div v-else class="onboarding">
            <el-button type="primary" round @click="router.push('/onboarding')">
              挑 3–5 部喜欢的作品
            </el-button>
          </div>

          <div class="quiz-entry">
            <el-button text type="primary" @click="router.push('/taste-quiz')">
              做口味测试
            </el-button>
          </div>
        </section>

      </aside>
    </section>

    <EntryDialog v-model="entryDialogVisible" :work="activeWork" @saved="handleSaved" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, MagicStick, Search } from '@element-plus/icons-vue'
import EntryDialog from '../components/EntryDialog.vue'
import WorkCard from '../components/WorkCard.vue'
import { useCatalogStore, type RecommendationParams } from '../store/game'
import type { Work } from '../types/api'

const store = useCatalogStore()
const router = useRouter()

const onboardKey = 'gal-love-onboard-v1'

function hasOnboardFlag(): boolean {
  try {
    return localStorage.getItem(onboardKey) === 'done'
  } catch {
    return false
  }
}

const showIntroBar = ref(!hasOnboardFlag())

function dismissIntroBar() {
  showIntroBar.value = false
  try {
    localStorage.setItem(onboardKey, 'done')
  } catch {
    // 隐私模式下写入失败时，仅隐藏本次会话的提示
  }
}

const search = ref('')
const entryDialogVisible = ref(false)
const activeWork = ref<Work | null>(null)
const addingId = ref<number | null>(null)

const counts = computed(() => store.entryCounts)

// 用当前设置发起推荐请求，保证推荐结果与设置页保持一致。
function recommendationParams(): RecommendationParams {
  const s = store.settings
  return {
    limit: 12,
    include_nsfw: s.include_nsfw,
    min_year: s.min_year ?? undefined,
    max_length_minutes: s.max_length_minutes ?? undefined,
    platform: s.platform ?? undefined,
    language: s.language ?? undefined,
    diversity: s.diversity,
  }
}

const tips = [
  { title: '高分作品', action: '去看看', to: '/explore?sort=rating' },
  { title: '按标签找', action: '去看看', to: '/explore' },
  { title: '推荐设置', action: '去看看', to: '/settings' },
]

function openSearch() {
  router.push({ path: '/explore', query: search.value.trim() ? { q: search.value.trim() } : {} })
}

function openEntry(work: Work) {
  activeWork.value = work
  entryDialogVisible.value = true
}

async function quickWant(work: Work) {
  addingId.value = work.id
  try {
    await store.saveEntry(work.id, { status: 'want' })
    ElMessage.success(`已把《${work.title}》加入想玩`)
    await store.fetchRecommendations(recommendationParams())
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    addingId.value = null
  }
}

async function notInterested(work: Work) {
  try {
    await store.markNotInterested(work.id)
    ElMessage.success('已记录反馈，会减少类似推荐')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  }
}

async function handleSaved() {
  await Promise.all([
    store.fetchRecommendations(recommendationParams()),
    store.fetchEntries(),
    store.loadStats(),
  ])
}

onMounted(async () => {
  await Promise.all([store.fetchEntries(), store.loadStats()])
  // 先加载设置，再据此请求推荐，避免首次进入时推荐与设置不一致。
  await store.fetchSettings()
  await store.fetchRecommendations(recommendationParams())
})
</script>

<style scoped>
.home {
  padding: 0 0 56px;
}

.intro-bar {
  background: linear-gradient(90deg, #efeaff, #f8eafc);
  border-bottom: 1px solid rgba(123, 92, 255, 0.16);
}

.intro-bar-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 10px 28px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #5f5878;
}

.intro-icon {
  color: #8a6cff;
  font-size: 18px;
}

.intro-text {
  flex: 1;
  line-height: 1.6;
}

.intro-text strong {
  color: #382e63;
}

.intro-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.intro-fade-enter-active,
.intro-fade-leave-active {
  transition: opacity 0.2s ease;
}

.intro-fade-enter-from,
.intro-fade-leave-to {
  opacity: 0;
}

.hero {
  background: linear-gradient(135deg, #241d44 0%, #3a2a63 100%);
  color: #fff;
  border-radius: 0 0 24px 24px;
}

.hero-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 44px 28px 48px;
}

.hero h1 {
  margin: 0 0 24px;
  font-size: clamp(32px, 4.5vw, 48px);
  line-height: 1.12;
  letter-spacing: -0.02em;
}

.search-row {
  display: flex;
  gap: 10px;
  max-width: 620px;
}

.layout {
  max-width: 1180px;
  margin: 0 auto;
  padding: 40px 28px 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 28px;
  align-items: start;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head.secondary {
  margin-top: 40px;
}

.section-head h2,
.panel h2 {
  margin: 0 0 6px;
  font-size: 22px;
}

.recommendation-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 18px;
  min-height: 120px;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.card-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.explore-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.tip-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  border: 1px solid rgba(31, 35, 64, 0.06);
}

.tip-card h3 {
  margin: 0 0 10px;
  font-size: 16px;
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 76px;
}

.panel {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  box-shadow: 0 10px 30px rgba(31, 35, 64, 0.05);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 18px 0;
}

.status-cell {
  text-align: center;
  padding: 12px 4px;
  border-radius: 10px;
  background: #f7f6fc;
}

.status-cell strong {
  display: block;
  font-size: 20px;
  color: #382e63;
}

.status-cell span {
  font-size: 12px;
  color: #8a8fa3;
}

.sub-title {
  margin: 18px 0 10px;
  font-size: 14px;
}

.taste-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.muted {
  color: #9a9fb0;
  font-size: 13px;
  line-height: 1.7;
}

.onboarding {
  text-align: center;
  padding: 20px 8px 8px;
}

.quiz-entry {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(31, 35, 64, 0.06);
  text-align: center;
}

@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .side-column {
    position: static;
  }

  .explore-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .search-row {
    flex-direction: column;
  }

  .intro-bar-inner {
    padding: 10px 16px;
    flex-wrap: wrap;
  }

  .intro-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .hero-inner {
    padding: 44px 20px 52px;
  }

  .layout {
    padding: 28px 16px 0;
  }
}
</style>
