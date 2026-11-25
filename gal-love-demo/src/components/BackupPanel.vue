<template>
  <section class="panel">
    <div class="panel-head">
      <div>
        <h2>备份与恢复</h2>
        <p class="panel-desc">恢复前会自动留一份当前数据。</p>
      </div>
      <el-button
        type="primary"
        :loading="creating"
        @click="createBackup"
      >
        <el-icon><Plus /></el-icon> 立即备份
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="backups"
      size="small"
      empty-text="还没有备份，点击「立即备份」创建第一个"
    >
      <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="大小" width="110">
        <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" align="right">
        <template #default="{ row }">
          <el-button
            link
            type="danger"
            :loading="restoring === row.filename"
            @click="restore(row)"
          >
            恢复
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '../api'
import type { BackupInfo } from '../types/api'

const emit = defineEmits<{
  changed: []
}>()

const loading = ref(false)
const creating = ref(false)
const restoring = ref('')
const backups = ref<BackupInfo[]>([])

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function formatTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatSize(bytes?: number): string {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes)) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

async function refresh() {
  loading.value = true
  try {
    backups.value = (await api.backups()).items
  } catch (error) {
    ElMessage.error(messageOf(error, '加载备份列表失败'))
  } finally {
    loading.value = false
  }
}

async function createBackup() {
  creating.value = true
  try {
    const result = await api.createBackup()
    ElMessage.success(`已创建备份：${result.filename}`)
    await refresh()
    emit('changed')
  } catch (error) {
    ElMessage.error(messageOf(error, '创建备份失败'))
  } finally {
    creating.value = false
  }
}

async function restore(backup: BackupInfo) {
  try {
    await ElMessageBox.confirm(
      `恢复备份「${backup.filename}」会覆盖当前数据库。系统会先把当前数据自动备份一份，确定继续吗？`,
      '恢复备份',
      {
        type: 'warning',
        confirmButtonText: '确认恢复',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  restoring.value = backup.filename
  try {
    const result = await api.restoreBackup(backup.filename)
    ElMessage.success(
      `已恢复备份「${result.filename}」，恢复前的安全备份为「${result.auto_backup.filename}」`,
    )
    await refresh()
    emit('changed')
  } catch (error) {
    ElMessage.error(messageOf(error, '恢复备份失败'))
  } finally {
    restoring.value = ''
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

@media (max-width: 560px) {
  .panel {
    padding: 16px;
  }
}
</style>
