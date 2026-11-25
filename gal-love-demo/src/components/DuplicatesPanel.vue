<template>
  <section class="panel">
    <div class="panel-head">
      <div>
        <h2>重复作品</h2>
        <p class="panel-desc">选择保留哪一部，再合并。</p>
      </div>
      <el-button text type="primary" :loading="loading" @click="refresh">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="candidates"
      size="small"
      empty-text="没有检测到重复作品"
    >
      <el-table-column label="作品 A" min-width="180">
        <template #default="{ row }">
          <span class="work-title">{{ titleOf(row.work_id) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="作品 B" min-width="180">
        <template #default="{ row }">
          <span class="work-title">{{ titleOf(row.other_id) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分数" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.score >= 0.9 ? 'danger' : 'warning'" effect="plain">
            {{ row.score.toFixed(2) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="相似点" min-width="220">
        <template #default="{ row }">
          <span class="reasons">{{ row.reasons.join('；') || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110" align="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openMerge(row)">查看 / 合并</el-button>
        </template>
      </el-table-column>
    </el-table>

    <MergeDialog
      v-if="active"
      v-model="dialogVisible"
      :candidate="active"
      :left="works.get(active.work_id) ?? null"
      :right="works.get(active.other_id) ?? null"
      @merged="onMerged"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import MergeDialog from './MergeDialog.vue'
import type { DuplicateCandidate, Work } from '../types/api'

const emit = defineEmits<{
  merged: []
}>()

const loading = ref(false)
const candidates = ref<DuplicateCandidate[]>([])
const works = reactive(new Map<number, Work | null>())
const active = ref<DuplicateCandidate | null>(null)
const dialogVisible = ref(false)

function titleOf(id: number): string {
  return works.get(id)?.title || `作品 #${id}`
}

async function loadWorks(ids: number[]) {
  await Promise.all(
    ids.map(async (id) => {
      if (works.has(id)) return
      try {
        works.set(id, await api.work(id))
      } catch {
        works.set(id, null)
      }
    }),
  )
}

async function refresh() {
  loading.value = true
  try {
    const items = (await api.duplicates(50, 0.75)).items
    const ids = [...new Set(items.flatMap((item) => [item.work_id, item.other_id]))]
    await loadWorks(ids)
    candidates.value = items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载重复候选失败')
  } finally {
    loading.value = false
  }
}

function openMerge(candidate: DuplicateCandidate) {
  active.value = candidate
  dialogVisible.value = true
}

async function onMerged() {
  emit('merged')
  await refresh()
}

onMounted(refresh)
</script>

<style scoped>
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-desc {
  margin: 0;
  color: #8a8fa3;
  font-size: 13px;
  line-height: 1.7;
  max-width: 620px;
}

.work-title {
  color: #362e5c;
  font-weight: 500;
}

.reasons {
  color: #8a8fa3;
  font-size: 12px;
}

@media (max-width: 560px) {
  .panel {
    padding: 16px;
  }
}
</style>
