<template>
  <div class="persona-page" v-loading="loading">
    <el-empty v-if="!loading && !detail" description="测试不存在或暂时不可用">
      <el-button type="primary" @click="router.push('/persona')">返回测试列表</el-button>
    </el-empty>

    <template v-else-if="detail">
      <header class="page-head">
        <el-button text class="back" @click="router.push('/persona')">
          <el-icon><ArrowLeft /></el-icon>测试列表
        </el-button>
        <div class="head-copy">
          <h1>{{ detail.title }}</h1>
          <p v-if="detail.subtitle" class="head-subtitle">{{ detail.subtitle }}</p>
        </div>
      </header>

      <section v-if="isRedirectKind" class="panel redirect-card">
        <el-button type="primary" size="large" @click="router.push(redirectTo)">
          {{ redirectLabel }}
        </el-button>
      </section>

      <template v-else-if="showResult && result">
        <section class="panel result-card">
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

          <div v-if="scoreBars.length" class="score-list">
            <div v-for="(bar, index) in scoreBars" :key="`${bar.name}-${index}`" class="score-row">
              <div class="score-head">
                <span>{{ bar.name }}</span>
                <span class="score-value">{{ bar.value }}</span>
              </div>
              <div class="score-track">
                <div class="score-fill" :style="{ width: `${bar.value}%` }" />
              </div>
            </div>
          </div>

          <div class="result-actions">
            <el-button type="primary" :loading="recLoading" @click="loadRecommendations">
              按这份画像看看推荐
            </el-button>
            <el-button @click="retake">重新作答</el-button>
            <el-button text type="primary" @click="router.push('/persona')">
              返回测试列表
            </el-button>
          </div>
        </section>

        <section v-if="showRecommend" class="recommend-section">
          <div class="section-head">
            <h2>推荐结果</h2>
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

      <section v-else-if="detail.kind === 'birthday'" class="panel birthday-card">
        <p class="hint">用于计算星座</p>
        <el-date-picker
          v-model="birthday"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择生日"
          size="large"
        />
        <div class="birthday-actions">
          <el-button type="primary" :loading="submitting" @click="submitBirthday">保存</el-button>
        </div>
      </section>

      <template v-else-if="currentQuestion">
        <div class="panel quiz-card">
          <div class="card-head">
            <span class="step">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
            <el-progress
              :percentage="progress"
              :show-text="false"
              :stroke-width="6"
              class="progress"
            />
          </div>

          <h2 class="question-title">{{ currentQuestion.title }}</h2>
          <p v-if="currentQuestion.subtitle" class="question-subtitle">
            {{ currentQuestion.subtitle }}
          </p>

          <div class="options">
            <button
              v-for="option in currentQuestion.options"
              :key="option.id"
              type="button"
              class="option-card"
              :class="{ selected: answers[currentQuestion.id] === option.id }"
              @click="selectOption(option.id)"
            >
              <span class="option-dot" />
              <span>{{ option.label }}</span>
            </button>
          </div>

          <div class="card-actions">
            <el-button :disabled="currentIndex === 0" @click="prev">上一题</el-button>
            <el-button type="primary" :loading="submitting" @click="next">
              {{ isLast ? '查看结果' : '下一题' }}
            </el-button>
          </div>
        </div>
      </template>

      <el-empty v-else description="暂无题目" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { api } from '../api'
import WorkCard from '../components/WorkCard.vue'
import type {
  PersonaDetailResponse,
  PersonaQuestion,
  PersonaResult,
  ProfileSource,
  Work,
} from '../types/api'

interface ScoreBar {
  name: string
  value: number
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const submitting = ref(false)
const recLoading = ref(false)
const detail = ref<PersonaDetailResponse | null>(null)
const answers = ref<Record<string, string>>({})
const result = ref<PersonaResult | null>(null)
const questions = ref<PersonaQuestion[]>([])
const currentIndex = ref(0)
const showResult = ref(false)
const showRecommend = ref(false)
const recommendations = ref<Work[]>([])
const birthday = ref('')

const key = computed(() => {
  const value = route.params.key
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '')
})

const currentQuestion = computed<PersonaQuestion | null>(
  () => questions.value[currentIndex.value] ?? null,
)
const isLast = computed(
  () => questions.value.length > 0 && currentIndex.value === questions.value.length - 1,
)
const progress = computed(() => {
  if (!questions.value.length) return 0
  return Math.round(((currentIndex.value + 1) / questions.value.length) * 100)
})
const isRedirectKind = computed(
  () => detail.value?.kind === 'pairwise' || detail.value?.kind === 'draw',
)
const redirectTo = computed(() =>
  detail.value?.kind === 'draw' ? '/persona/tarot' : '/persona/pairwise',
)
const redirectLabel = computed(() =>
  detail.value?.kind === 'draw' ? '去抽一张' : '开始二选一',
)

const SCORE_LABELS: Record<string, Record<string, string>> = {
  bigfive: { O: '开放性', C: '尽责性', E: '外向性', A: '宜人性', N: '神经质' },
  enneagram: {
    '1': '完美型',
    '2': '助人型',
    '3': '成就型',
    '4': '自我型',
    '5': '观察型',
    '6': '忠诚型',
    '7': '活跃型',
    '8': '领袖型',
    '9': '和平型',
  },
  motivation: {
    Story: '剧情',
    Fantasy: '幻想',
    Design: '设计',
    Discovery: '探索',
    Challenge: '挑战',
    Completion: '收集',
    Community: '社群',
    Excitement: '节奏',
  },
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)))
}

function toScoreBar(name: string, value: unknown): ScoreBar | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return { name, value: clampScore(value) }
  }
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, unknown>
    const score = record.score ?? record.value
    if (typeof score === 'number' && Number.isFinite(score)) {
      const label = typeof record.label === 'string' ? record.label : name
      return { name: label, value: clampScore(score) }
    }
  }
  return null
}

const scoreBars = computed<ScoreBar[]>(() => {
  const scores = result.value?.scores
  if (!scores || typeof scores !== 'object' || Array.isArray(scores)) return []
  const labels = SCORE_LABELS[key.value]
  return Object.entries(scores as Record<string, unknown>)
    .map(([name, value]) => toScoreBar(labels?.[name] ?? name, value))
    .filter((bar): bar is ScoreBar => bar !== null)
})

function resetState() {
  answers.value = {}
  result.value = null
  questions.value = []
  currentIndex.value = 0
  showResult.value = false
  showRecommend.value = false
  recommendations.value = []
  birthday.value = ''
}

function applySaved(data: PersonaDetailResponse) {
  detail.value = data
  questions.value = data.questions
  answers.value = { ...data.answers }
  result.value = data.result
  showResult.value = true
}

function selectOption(optionId: string) {
  const question = currentQuestion.value
  if (!question || submitting.value) return
  answers.value = { ...answers.value, [question.id]: optionId }
  if (isLast.value) {
    void submit()
    return
  }
  currentIndex.value += 1
}

function prev() {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

function next() {
  const question = currentQuestion.value
  if (question && !answers.value[question.id]) {
    ElMessage.warning('请选择一项')
    return
  }
  if (!isLast.value) {
    currentIndex.value += 1
    return
  }
  void submit()
}

async function submit() {
  if (!detail.value || !key.value) return
  const missingIndex = questions.value.findIndex((question) => !answers.value[question.id])
  if (missingIndex !== -1) {
    currentIndex.value = missingIndex
    ElMessage.warning('请完成所有题目')
    return
  }
  submitting.value = true
  try {
    const data = await api.savePersona(key.value, answers.value)
    applySaved(data)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

async function submitBirthday() {
  if (!key.value) return
  if (!birthday.value) {
    ElMessage.warning('请选择生日')
    return
  }
  submitting.value = true
  try {
    const data = await api.savePersona(key.value, { birthday: birthday.value })
    applySaved(data)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    submitting.value = false
  }
}

async function loadRecommendations() {
  if (!key.value) return
  recLoading.value = true
  showRecommend.value = true
  try {
    const data = await api.recommendations({
      limit: 12,
      profile_source: key.value as ProfileSource,
      save: false,
    })
    recommendations.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '推荐加载失败')
  } finally {
    recLoading.value = false
  }
}

function retake() {
  showResult.value = false
  result.value = null
  answers.value = {}
  birthday.value = ''
  recommendations.value = []
  showRecommend.value = false
  currentIndex.value = 0
}

async function load() {
  const currentKey = key.value
  resetState()
  if (!currentKey) {
    detail.value = null
    loading.value = false
    return
  }
  loading.value = true
  try {
    const data = await api.persona(currentKey)
    detail.value = data
    questions.value = data.questions
    answers.value = { ...data.answers }
    result.value = data.result
    if (data.kind === 'birthday') {
      birthday.value = data.answers.birthday ?? ''
    }
    if (data.result.completed) {
      showResult.value = true
    } else if (data.kind === 'questionnaire') {
      const nextIndex = data.questions.findIndex((question) => !data.answers[question.id])
      currentIndex.value = nextIndex === -1 ? 0 : nextIndex
    }
  } catch (error) {
    detail.value = null
    ElMessage.error(error instanceof Error ? error.message : '测试加载失败')
  } finally {
    loading.value = false
  }
}

watch(key, () => void load(), { immediate: true })
</script>

<style scoped>
.persona-page {
  max-width: 900px;
  min-height: 200px;
  margin: 0 auto;
  padding: 24px 24px 56px;
}

.page-head {
  margin-bottom: 20px;
}

.back {
  padding-left: 0;
  color: #7c6fae;
}

.head-copy h1 {
  margin: 6px 0 4px;
  font-size: 28px;
  color: #2f274a;
}

.head-subtitle {
  margin: 0;
  font-size: 14px;
  color: #9a8fa3;
}

.panel {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  box-shadow: 0 12px 32px rgba(93, 68, 168, 0.08);
}

.redirect-card {
  padding: 40px 28px;
  text-align: center;
}

.birthday-card {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  align-items: flex-start;
}

.hint {
  margin: 0;
  font-size: 14px;
  color: #8a8fa3;
}

.birthday-actions {
  display: flex;
  gap: 12px;
}

.quiz-card {
  padding: 28px;
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

.options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 16px;
  font: inherit;
  font-size: 15px;
  color: #4b4365;
  background: #faf9ff;
  border: 1px solid rgba(31, 35, 64, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.option-card:hover {
  border-color: #a99be8;
}

.option-card.selected {
  border-color: #6f57d9;
  background: #f1eefd;
  box-shadow: 0 4px 14px rgba(111, 87, 217, 0.15);
  color: #3a2e63;
  font-weight: 600;
}

.option-dot {
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #b7a9e6;
  box-sizing: border-box;
}

.option-card.selected .option-dot {
  border: 5px solid #6f57d9;
}

.card-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 26px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.result-card {
  padding: 28px;
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

.score-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 460px;
  margin: 26px auto 0;
  text-align: left;
}

.score-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 13px;
  color: #4b4365;
}

.score-value {
  font-weight: 600;
  color: #6f57d9;
}

.score-track {
  height: 8px;
  overflow: hidden;
  background: #efeaff;
  border-radius: 999px;
}

.score-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6f57d9, #b06ab3);
  transition: width 0.3s ease;
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 26px;
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

@media (max-width: 560px) {
  .persona-page {
    padding: 16px 14px 40px;
  }

  .quiz-card,
  .result-card,
  .birthday-card {
    padding: 20px 16px;
  }

  .options {
    grid-template-columns: 1fr;
  }

  .question-title {
    font-size: 20px;
  }

  .head-copy h1 {
    font-size: 22px;
  }
}
</style>
