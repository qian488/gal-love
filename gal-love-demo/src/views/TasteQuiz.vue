<template>
  <div class="quiz-page" v-loading="loading">
    <template v-if="!showResult">
      <div v-if="currentQuestion" class="quiz-card">
        <div class="card-head">
          <span class="step">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <el-progress
            :percentage="progress"
            :show-text="false"
            :stroke-width="6"
            class="progress"
          />
        </div>

        <h1 class="question-title">{{ currentQuestion.title }}</h1>
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
            {{ isLast ? '提交' : '下一题' }}
          </el-button>
        </div>
      </div>

      <el-empty v-else description="暂无题目" />
    </template>

    <template v-else-if="result">
      <section class="result-card">
        <span class="eyebrow">RESULT</span>
        <h1 class="result-code">{{ result.code }}</h1>
        <div class="result-labels">
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
        <el-button class="retake-btn" @click="retake">
          <el-icon><RefreshRight /></el-icon>重新作答
        </el-button>
      </section>

      <section class="recommend-section">
        <div class="section-head">
          <h2>按这份问卷推荐</h2>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import { api } from '../api'
import WorkCard from '../components/WorkCard.vue'
import type { TasteQuizQuestion, TasteQuizResult, Work } from '../types/api'

const loading = ref(true)
const submitting = ref(false)
const recLoading = ref(false)
const questions = ref<TasteQuizQuestion[]>([])
const answers = ref<Record<string, string>>({})
const result = ref<TasteQuizResult | null>(null)
const currentIndex = ref(0)
const showResult = ref(false)
const recommendations = ref<Work[]>([])

const currentQuestion = computed(() => questions.value[currentIndex.value] ?? null)
const isLast = computed(() => currentIndex.value === questions.value.length - 1)
const progress = computed(() => {
  if (!questions.value.length) return 0
  return Math.round(((currentIndex.value + 1) / questions.value.length) * 100)
})

function selectOption(optionId: string) {
  const question = currentQuestion.value
  if (!question) return
  answers.value = { ...answers.value, [question.id]: optionId }
}

function prev() {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

async function next() {
  if (!isLast.value) {
    currentIndex.value += 1
    return
  }
  await submit()
}

async function submit() {
  const missing = questions.value.find((question) => !answers.value[question.id])
  if (missing) {
    ElMessage.warning('请完成所有题目')
    return
  }
  submitting.value = true
  try {
    const data = await api.saveTasteQuiz(answers.value)
    answers.value = { ...data.answers }
    result.value = data.result
    showResult.value = true
    await loadRecommendations()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

async function loadRecommendations() {
  recLoading.value = true
  try {
    const data = await api.recommendations({
      limit: 12,
      profile_source: 'quiz',
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
  answers.value = {}
  result.value = null
  recommendations.value = []
  currentIndex.value = 0
  showResult.value = false
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await api.tasteQuiz()
    questions.value = data.questions
    answers.value = { ...data.answers }
    result.value = data.result
    if (data.result?.completed) {
      showResult.value = true
      await loadRecommendations()
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '题目加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.quiz-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 36px 24px 56px;
}

.quiz-card,
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

.retake-btn {
  margin-top: 22px;
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
  .quiz-page {
    padding: 20px 14px 40px;
  }

  .quiz-card,
  .result-card {
    padding: 20px 16px;
  }

  .options {
    grid-template-columns: 1fr;
  }

  .question-title {
    font-size: 20px;
  }
}
</style>
