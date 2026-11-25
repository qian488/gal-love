<template>
  <section class="panel">
    <div class="panel-head">
      <div>
        <h2>投票库</h2>
      </div>
      <el-button text type="primary" :loading="loading" @click="refresh">
        <el-icon><Refresh /></el-icon> 刷新统计
      </el-button>
    </div>

    <el-descriptions v-loading="loading" :column="2" border size="small" class="stats-desc">
      <el-descriptions-item label="状态">
        <el-tag size="small" :type="stats?.available ? 'success' : 'danger'" effect="plain">
          {{ stats?.available ? '可用' : '不可用' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="投票数">
        {{ formatNumber(stats?.votes) }}
      </el-descriptions-item>
      <el-descriptions-item label="用户数">
        {{ formatNumber(stats?.users) }}
      </el-descriptions-item>
      <el-descriptions-item label="作品条目数">
        {{ formatNumber(stats?.items) }}
      </el-descriptions-item>
      <el-descriptions-item label="平均分数">
        {{ stats?.mean_score == null ? '—' : stats.mean_score.toFixed(2) }}
      </el-descriptions-item>
      <el-descriptions-item label="单作票数范围">
        {{ formatNumber(stats?.min_vote_count) }} – {{ formatNumber(stats?.max_vote_count) }}
      </el-descriptions-item>
    </el-descriptions>

    <el-divider />

    <div class="import-block">
      <h3>从 VNDB dump 导入票数</h3>
      <div class="form-grid">
        <label class="field path-field">
          <span>dump 文件路径</span>
          <el-input v-model="dumpPath" placeholder="例如：/data/vndb-votes.txt" clearable />
        </label>
        <label class="field">
          <span>最少投票数</span>
          <el-input-number v-model="minVotes" :min="0" :step="10" controls-position="right" />
        </label>
        <label class="field">
          <span>最多导入条数</span>
          <el-input-number
            v-model="limit"
            :min="1"
            :step="1000"
            controls-position="right"
            placeholder="不限"
          />
        </label>
      </div>
      <div class="actions">
        <el-button type="primary" :loading="importing" @click="importVotes">导入票数</el-button>
        <small>留空不限制条数。</small>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import type { VotesStats } from '../types/api'

const loading = ref(false)
const importing = ref(false)
const stats = ref<VotesStats | null>(null)

const dumpPath = ref('')
const minVotes = ref(0)
const limit = ref<number | undefined>(undefined)

function formatNumber(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('zh-CN') : '—'
}

async function refresh() {
  loading.value = true
  try {
    stats.value = await api.votesStats()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载投票库统计失败')
  } finally {
    loading.value = false
  }
}

async function importVotes() {
  if (!dumpPath.value.trim()) {
    ElMessage.warning('请填写 dump 文件路径')
    return
  }
  importing.value = true
  try {
    const result = await api.importVotes({
      dump_path: dumpPath.value.trim(),
      min_votes: minVotes.value,
      limit: limit.value,
    })
    ElMessage.success(
      `导入完成：${result.items_imported} 个条目、${result.votes_imported} 张投票、${result.users} 位用户`,
    )
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入投票失败')
  } finally {
    importing.value = false
  }
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

.stats-desc {
  font-size: 13px;
}

.import-block h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  align-items: end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #8a8fa3;
}

.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}

.actions small {
  color: #9a9fb0;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .panel {
    padding: 16px;
  }
}
</style>
