<template>
  <div class="pairwise-page" v-loading="loading">
    <template v-if="!finished">
      <div class="pairwise-card">
        <div class="card-head">
          <span class="step">已答 {{ answered }} / {{ TOTAL_ROUNDS }}</span>
          <el-progress
            :percentage="progress"
            :show-text="false"
            :stroke-width="6"
            class="progress"
          />
        </div>

        <h1 class="question-title">这两部，更想玩哪一部？</h1>
        <p class="question-subtitle">凭第一感觉选一部就好</p>

        <div v-if="pair" class="duel">
          <button
            type="button"
            class="work-choice"
            :disabled="submitting"
            @click="choose(pair.left, pair.right)"
          >
            <div class="cover-wrap">
              <CoverImage
                :src="pair.left.cover_url || undefined"
                :title="displayTitle(pair.left)"
                ratio="4 / 3"
              />
            </div>
            <div class="choice-body">
              <h2 class="choice-title">{{ displayTitle(pair.left) }}</h2>
              <p v-if="metaText(pair.left)" class="choice-meta">{{ metaText(pair.left) }}</p>
              <div v-if="tagNames(pair.left).length" class="choice-tags">
                <el-tag
                  v-for="tag in tagNames(pair.left)"
                  :key="tag"
                  size="small"
                  effect="plain"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </button>

          <span class="vs-badge" aria-hidden="true">VS</span>

          <button
            type="button"
            class="work-choice"
            :disabled="submitting"
            @click="choose(pair.right, pair.left)"
          >
            <div class="cover-wrap">
              <CoverImage
                :src="pair.right.cover_url || undefined"
                :title="displayTitle(pair.right)"
                ratio="4 / 3"
              />
            </div>
            <div class="choice-body">
              <h2 class="choice-title">{{ displayTitle(pair.right) }}</h2>
              <p v-if="metaText(pair.right)" class="choice-meta">{{ metaText(pair.right) }}</p>
              <div v-if="tagNames(pair.right).length" class="choice-tags">
                <el-tag
                  v-for="tag in tagNames(pair.right)"
                  :key="tag"
                  size="small"
                  effect="plain"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </button>
        </div>

        <div v-else-if="noPairs" class="duel-empty">
          <el-empty description="作品不够，先去导入一些数据" />
        </div>

        <div v-else-if="!loading" class="duel-empty">
          <el-empty description="暂时没有可选的组合">
            <el-button @click="loadPair">重试</el-button>
          </el-empty>
        </div>

        <div v-if="pair" class="skip-row">
          <el-button text :disabled="submitting" @click="skip">都不想玩</el-button>
        </div>
      </div>
    </template>

    <template v-else-if="result">
      <section class="result-card">
        <span class="eyebrow">RESULT</span>
        <h1 class="result-code">{{ result.code }}</h1>
        <div v-if="result.labels.length" class="result-labels">
          <el-tag
            v-for="label in result.labels"
            :key="label"
            round
            effect="light"
            type="primary"
            class="result-tag"
          >
            {{ label }}
          </el-tag>
        </div>
        <p v-else class="result-muted">这次没有拼出标签</p>

        <div class="result-actions">
          <el-button type="primary" :loading="recLoading" @click="loadRecommendations">
            按这个画像看看推荐
          </el-button>
          <el-button :disabled="recLoading" @click="restart">
            <el-icon><RefreshRight /></el-icon>重新开始
          </el-button>
        </div>
      </section>

      <section v-if="showRecommendations" class="recommend-section">
        <div class="section-head">
          <h2>为你推荐</h2>
        </div>
        <div v-loading="recLoading" class="recommend-list">
          <WorkCard v-for="work in recommendations" :key="work.id" :work="work" />
        </div>
        <el-empty
          v-if="!recLoading && !recommendations.length"
          description="暂时没有匹配的推荐"
        />
      </section>
    </template>

    <el-empty v-else description="还没有画像结果">
      <el-button type="primary" @click="restart">重新开始</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import { api } from '../api'
import CoverImage from '../components/CoverImage.vue'
import WorkCard from '../components/WorkCard.vue'
import type { PersonaResult, PairwisePair, Work } from '../types/api'

const TOTAL_ROUNDS = 10

const loading = ref(true)
const submitting = ref(false)
const recLoading = ref(false)
const pair = ref<PairwisePair | null>(null)
const answered = ref(0)
const result = ref<PersonaResult | null>(null)
const finished = ref(false)
const noPairs = ref(false)
const recommendations = ref<Work[]>([])
const showRecommendations = ref(false)

const progress = computed(() =>
  Math.round((Math.min(answered.value, TOTAL_ROUNDS) / TOTAL_ROUNDS) * 100),
)

function displayTitle(work: Work): string {
  return work.title_zh?.trim() || work.title
}

function lengthText(minutes: number): string {
  if (minutes >= 60) {
    return `约 ${Math.round(minutes / 60)} 小时`
  }
  return `${minutes} 分钟`
}

function metaText(work: Work): string {
  const parts: string[] = []
  if (work.release_year) parts.push(String(work.release_year))
  if (work.length_minutes) parts.push(lengthText(work.length_minutes))
  return parts.join(' · ')
}

function tagNames(work: Work): string[] {
  return work.tags
    .slice(0, 3)
    .map((tag) => tag.name_zh?.trim() || tag.name)
    .filter((name) => Boolean(name))
}

function readAnswered(data: PersonaResult | null): number | null {
  const raw = data?.['answered']
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : null
}

async function loadPair() {
  pair.value = null
  noPairs.value = false
  loading.value = true
  try {
    const data = await api.pairwiseNext()
    const next = data.pairs[0] ?? null
    if (!next) {
      noPairs.value = true
      return
    }
    pair.value = next
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '出题失败')
  } finally {
    loading.value = false
  }
}

async function choose(winner: Work, loser: Work, skipped = false) {
  if (submitting.value) return
  submitting.value = true
  try {
    const data = await api.pairwiseAnswer({
      winner_id: winner.id,
      loser_id: loser.id,
      skipped,
    })
    result.value = data.payload.result
    const reported = readAnswered(data.payload.result)
    answered.value =
      reported !== null && reported > answered.value ? reported : answered.value + 1

    if (answered.value >= TOTAL_ROUNDS) {
      finished.value = true
      pair.value = null
      return
    }

    await loadPair()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

function skip() {
  if (!pair.value) return
  void choose(pair.value.left, pair.value.right, true)
}

async function loadRecommendations() {
  showRecommendations.value = true
  recLoading.value = true
  try {
    const data = await api.recommendations({
      limit: 12,
      profile_source: 'pairwise',
      save: false,
    })
    recommendations.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '推荐加载失败')
  } finally {
    recLoading.value = false
  }
}

async function restart() {
  loading.value = true
  try {
    await api.pairwiseReset()
    answered.value = 0
    result.value = null
    finished.value = false
    recommendations.value = []
    showRecommendations.value = false
    await loadPair()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '重置失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadPair()
})
</script>

<style scoped>
.pairwise-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 36px 24px 56px;
}

.pairwise-card,
.result-card {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  box-shadow: 0 12px 32px rgba(93, 68, 168, 0.08);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.step {
  font-size: 13px;
  color: #7c6fae;
  white-space: nowrap;
  font-weight: 600;
}

.progress {
  flex: 1;
}

.progress :deep(.el-progress-bar__outer) {
  background: #efeaff;
}

.progress :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #6f57d9, #b06ab3);
}

.question-title {
  margin: 0 0 6px;
  font-size: 24px;
  color: #2f274a;
}

.question-subtitle {
  margin: 0 0 24px;
  font-size: 14px;
  color: #9a8fa3;
}

.duel {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  min-height: 260px;
}

.vs-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #fff;
  color: #6f57d9;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: 0 6px 18px rgba(93, 68, 168, 0.18);
  border: 1px solid rgba(111, 87, 217, 0.18);
}

.work-choice {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 0;
  font: inherit;
  text-align: left;
  color: inherit;
  background: #faf9ff;
  border: 1px solid rgba(31, 35, 64, 0.08);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.work-choice:hover {
  border-color: #a99be8;
  box-shadow: 0 10px 26px rgba(93, 68, 168, 0.12);
  transform: translateY(-3px);
}

.work-choice:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.cover-wrap {
  --cover-placeholder-size: 2.6rem;
}

.choice-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
}

.choice-title {
  margin: 0;
  font-size: 17px;
  line-height: 1.4;
  color: #2f274a;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.choice-meta {
  margin: 0;
  font-size: 12px;
  color: #8a8fa3;
}

.choice-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.duel-empty {
  padding: 12px 0;
}

.skip-row {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.result-card {
  text-align: center;
}

.result-code {
  margin: 12px 0 18px;
  font-size: clamp(24px, 4vw, 32px);
  color: #382e63;
}

.result-labels {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.result-tag {
  font-size: 13px;
}

.result-muted {
  margin: 0;
  font-size: 13px;
  color: #9a8fa3;
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.result-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.recommend-section {
  margin-top: 32px;
}

.section-head {
  margin-bottom: 16px;
}

.section-head h2 {
  margin: 0;
  font-size: 21px;
  color: #2f274a;
}

.recommend-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  min-height: 60px;
}

@media (max-width: 720px) {
  .duel {
    grid-template-columns: 1fr;
  }

  .vs-badge {
    display: none;
  }
}

@media (max-width: 560px) {
  .pairwise-page {
    padding: 20px 14px 40px;
  }

  .pairwise-card,
  .result-card {
    padding: 20px 16px;
  }

  .question-title {
    font-size: 20px;
  }
}
</style>
