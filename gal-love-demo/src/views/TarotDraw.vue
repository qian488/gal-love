<template>
  <div class="tarot-page">
    <section class="draw-panel">
      <span class="eyebrow">TAROT</span>
      <h1 class="panel-title">抽牌</h1>
      <p class="panel-sub">选好牌阵，看看今天指向哪几部作品</p>

      <div class="spread-row">
        <el-radio-group v-model="spread" :disabled="drawing" class="spread-group">
          <el-radio-button :value="1">1 张 · 今日指引</el-radio-button>
          <el-radio-button :value="3">3 张 · 主题 / 阻碍 / 建议</el-radio-button>
        </el-radio-group>

        <el-button type="primary" :loading="drawing" @click="startDraw">
          <el-icon v-if="!drawing"><MagicStick /></el-icon>
          {{ drawData ? '再抽一次' : '抽牌' }}
        </el-button>
      </div>

      <div v-if="drawData" class="cards" :class="{ 'is-single': drawData.cards.length === 1 }">
        <article
          v-for="card in drawData.cards"
          :key="card.id + card.position"
          class="tarot-card"
          :class="{ 'is-reversed': card.reversed }"
        >
          <span v-if="card.reversed" class="reverse-badge">逆位</span>
          <span class="position">{{ card.position }}</span>
          <h2 class="card-name">{{ card.name_zh }}</h2>
          <p class="card-name-en">{{ card.name }}</p>
          <div v-if="card.themes.length" class="themes">
            <el-tag
              v-for="theme in card.themes"
              :key="theme"
              size="small"
              effect="plain"
              class="theme-tag"
            >
              {{ theme }}
            </el-tag>
          </div>
          <p v-if="card.meaning" class="meaning">{{ card.meaning }}</p>
        </article>
      </div>

      <el-empty
        v-else-if="drawData"
        description="这次没有抽到牌，再试一次"
      />

      <el-empty v-else-if="!drawing" description="选好牌阵，点上方按钮抽牌" />
    </section>

    <template v-if="drawData">
      <section class="works-section">
        <div class="section-head">
          <h2>这些牌指向的作品</h2>
        </div>
        <div class="works-grid">
          <WorkCard v-for="work in drawData.items" :key="work.id" :work="work" />
        </div>
        <el-empty
          v-if="!drawData.items.length"
          description="这次没有匹配到作品，再抽一次试试"
        />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { api } from '../api'
import WorkCard from '../components/WorkCard.vue'
import type { TarotDrawResponse } from '../types/api'

const spread = ref(1)
const drawing = ref(false)
const drawData = ref<TarotDrawResponse | null>(null)

async function startDraw() {
  drawing.value = true
  try {
    const data = await api.tarotDraw(spread.value)
    drawData.value = data
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '抽牌失败')
  } finally {
    drawing.value = false
  }
}
</script>

<style scoped>
.tarot-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 36px 24px 56px;
}

.draw-panel {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  box-shadow: 0 12px 32px rgba(93, 68, 168, 0.08);
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.panel-title {
  margin: 8px 0 4px;
  font-size: 24px;
  color: #2f274a;
}

.panel-sub {
  margin: 0 0 22px;
  font-size: 14px;
  color: #9a8fa3;
}

.spread-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(31, 35, 64, 0.06);
}

.spread-group :deep(.el-radio-button__inner) {
  border-color: #e5dffa;
  color: #5b5478;
}

.spread-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #6f57d9;
  border-color: #6f57d9;
  box-shadow: -1px 0 0 0 #6f57d9;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.cards.is-single {
  grid-template-columns: minmax(0, 320px);
  justify-content: center;
}

.tarot-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 22px 18px 20px;
  border-radius: 14px;
  background: linear-gradient(180deg, #faf9ff 0%, #f4f0ff 100%);
  border: 1px solid rgba(111, 87, 217, 0.16);
  box-shadow: 0 8px 22px rgba(93, 68, 168, 0.07);
}

.tarot-card.is-reversed {
  background: linear-gradient(180deg, #f7f7fa 0%, #efeef6 100%);
  border-color: rgba(120, 116, 140, 0.2);
  border-style: dashed;
}

.reverse-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 18px;
  color: #7c748f;
  background: rgba(124, 116, 143, 0.12);
}

.position {
  font-size: 11px;
  letter-spacing: 0.14em;
  color: #9a8fd0;
}

.card-name {
  margin: 0;
  font-size: 20px;
  line-height: 1.35;
  color: #382e63;
}

.card-name-en {
  margin: -2px 0 0;
  font-size: 12px;
  color: #9a8fa3;
}

.themes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.theme-tag {
  border-radius: 999px;
}

.meaning {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #5b5478;
}

.works-section {
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

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  min-height: 60px;
}

@media (max-width: 720px) {
  .cards {
    grid-template-columns: 1fr;
  }

  .cards.is-single {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .tarot-page {
    padding: 20px 14px 40px;
  }

  .draw-panel {
    padding: 20px 16px;
  }

  .panel-title {
    font-size: 20px;
  }

  .spread-row {
    flex-direction: column;
    align-items: stretch;
  }

  .spread-group {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
