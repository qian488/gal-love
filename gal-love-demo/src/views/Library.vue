<template>
  <div class="library">
    <header class="page-head">
      <div>
        <span class="eyebrow">MY LIBRARY</span>
        <h1>我的游戏库</h1>
        <p>记录状态、评分和笔记。</p>
      </div>
      <el-button type="primary" @click="router.push('/explore')">继续找作品</el-button>
    </header>

    <section class="stat-row">
      <div class="stat-card">
        <strong>{{ store.entryCounts.finished }}</strong>
        <span>玩过</span>
      </div>
      <div class="stat-card">
        <strong>{{ store.entryCounts.playing }}</strong>
        <span>在玩</span>
      </div>
      <div class="stat-card">
        <strong>{{ store.entryCounts.want }}</strong>
        <span>想玩</span>
      </div>
      <div class="stat-card">
        <strong>{{ store.entryCounts.dropped }}</strong>
        <span>弃坑</span>
      </div>
      <div class="stat-card accent">
        <strong>{{ favoriteCount }}</strong>
        <span>特别喜欢</span>
      </div>
    </section>

    <section class="toolbar">
      <el-radio-group v-model="statusFilter">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button
          v-for="(label, value) in entryStatusLabels"
          :key="value"
          :value="value"
        >
          {{ label }}
        </el-radio-button>
      </el-radio-group>
      <span class="count">{{ filtered.length }} 部</span>
    </section>

    <div v-loading="store.loadingEntries" class="entry-list">
      <article
        v-for="work in filtered"
        :key="work.id"
        class="entry-row"
        @click="router.push({ name: 'WorkDetail', params: { id: work.id } })"
      >
        <div class="thumb">
          <CoverImage :src="work.cover_url || undefined" :title="work.title" />
        </div>

        <div class="entry-main">
          <div class="entry-title-row">
            <div class="entry-title">
              <h2>{{ work.title }}</h2>
              <p v-if="zhAliasFor(work)" class="alias">{{ zhAliasFor(work) }}</p>
            </div>
            <el-tag
              v-if="work.entry"
              :color="entryStatusColors[work.entry.status]"
              effect="dark"
              size="small"
              round
            >
              {{ entryStatusLabels[work.entry.status] }}
            </el-tag>
            <el-tag v-if="work.entry?.favorite" type="warning" size="small" round>★ 特别喜欢</el-tag>
          </div>

          <p class="meta">
            {{ work.release_year || '未知年份' }}
            <template v-if="work.companies.length"> · {{ work.companies[0] }}</template>
            <template v-if="work.entry?.updated_at"> · 更新于 {{ formatDate(work.entry.updated_at) }}</template>
          </p>

          <p v-if="work.entry?.notes" class="notes">{{ work.entry.notes }}</p>

          <div class="tags">
            <el-tag
              v-for="tag in work.tags.slice(0, 5)"
              :key="tag.name"
              size="small"
              effect="plain"
              round
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </div>

        <div class="entry-side">
          <div class="my-rating">
            <template v-if="work.entry?.rating">
              <strong>{{ work.entry.rating }}</strong>
              <span>/ 10</span>
            </template>
            <span v-else class="muted">未评分</span>
          </div>
          <div class="row-actions" @click.stop>
            <el-button size="small" @click="openEntry(work)">编辑</el-button>
            <el-button size="small" text type="danger" @click="remove(work)">移除</el-button>
          </div>
        </div>
      </article>

      <el-empty
        v-if="!store.loadingEntries && !filtered.length"
        description="游戏库还是空的，先记录一部喜欢的作品吧"
      >
        <el-button type="primary" @click="router.push('/explore')">去探索</el-button>
      </el-empty>
    </div>

    <EntryDialog v-model="dialogVisible" :work="activeWork" @saved="handleSaved" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import CoverImage from '../components/CoverImage.vue'
import EntryDialog from '../components/EntryDialog.vue'
import { entryStatusColors, entryStatusLabels } from '../api'
import { useCatalogStore } from '../store/game'
import type { EntryStatus, Work } from '../types/api'

const router = useRouter()
const store = useCatalogStore()

const statusFilter = ref<'all' | EntryStatus>('all')
const dialogVisible = ref(false)
const activeWork = ref<Work | null>(null)

const filtered = computed(() => {
  if (statusFilter.value === 'all') return store.entries
  return store.entries.filter((work) => work.entry?.status === statusFilter.value)
})

const favoriteCount = computed(
  () => store.entries.filter((work) => work.entry?.favorite).length,
)

function zhAliasFor(work: Work): string {
  const title = (work.titles ?? []).find((item) => item.lang.toLowerCase().startsWith('zh'))
  return title && title.title !== work.title ? title.title : ''
}

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN')
}

function openEntry(work: Work) {
  activeWork.value = work
  dialogVisible.value = true
}

async function remove(work: Work) {
  try {
    await ElMessageBox.confirm(`确定从游戏库移除《${work.title}》吗？`, '移除记录', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await store.removeEntry(work.id)
    ElMessage.success('已移除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '移除失败')
  }
}

async function handleSaved() {
  await store.fetchEntries()
}

onMounted(() => {
  store.fetchEntries()
})
</script>

<style scoped>
.library {
  max-width: 1120px;
  margin: 0 auto;
  padding: 36px 28px 56px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 24px;
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

.stat-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.stat-card {
  background: #fff;
  border-radius: 14px;
  padding: 16px 18px;
  border: 1px solid rgba(31, 35, 64, 0.06);
}

.stat-card strong {
  display: block;
  font-size: 26px;
  color: #362e5c;
}

.stat-card span {
  font-size: 12px;
  color: #8a8fa3;
}

.stat-card.accent {
  background: linear-gradient(135deg, #f4efff, #fff6fb);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.count {
  color: #8a8fa3;
  font-size: 13px;
}

.entry-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 200px;
}

.entry-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) auto;
  gap: 18px;
  padding: 16px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.entry-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(31, 35, 64, 0.08);
}

.thumb {
  width: 92px;
  aspect-ratio: 3 / 4;
  border-radius: 10px;
  overflow: hidden;
  background: linear-gradient(135deg, #ddd8ff, #f4e7ff);
  --cover-placeholder-size: 28px;
}

.entry-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.entry-title-row h2 {
  margin: 0;
  font-size: 18px;
}

.alias {
  margin: 0;
  font-size: 12px;
  color: #9a8fd0;
}

.meta {
  margin: 6px 0;
  font-size: 12px;
  color: #8a8fa3;
}

.notes {
  margin: 8px 0;
  font-size: 13px;
  color: #625c7c;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.entry-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.my-rating strong {
  font-size: 24px;
  color: #e6a23c;
}

.my-rating span {
  font-size: 12px;
  color: #9a9fb0;
}

.muted {
  font-size: 13px;
  color: #9a9fb0;
}

.row-actions {
  display: flex;
  gap: 4px;
}

.row-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

@media (max-width: 760px) {
  .library {
    padding: 24px 16px 40px;
  }

  .stat-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .entry-row {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .thumb {
    width: 72px;
  }

  .entry-side {
    grid-column: 1 / -1;
    flex-direction: row;
    align-items: center;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
