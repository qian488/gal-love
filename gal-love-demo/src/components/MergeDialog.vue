<template>
  <el-dialog
    v-model="visible"
    title="合并重复作品"
    width="min(720px, 94vw)"
    destroy-on-close
  >
    <div class="merge-intro">
      <p>
        检测到疑似重复的两部作品，相似分数
        <strong>{{ candidate.score.toFixed(2) }}</strong>。
      </p>
      <div class="reasons">
        <el-tag
          v-for="(reason, index) in candidate.reasons"
          :key="index"
          size="small"
          effect="plain"
        >
          {{ reason }}
        </el-tag>
      </div>
    </div>

    <p class="keep-hint">
      请选择<strong>保留</strong>哪一部：另一部的游戏记录、反馈等数据会迁移到它，随后被删除。
    </p>

    <div class="choice-grid">
      <div
        v-for="side in sides"
        :key="side.id"
        class="work-card"
        :class="{ selected: keepId === side.id }"
        @click="keepId = side.id"
      >
        <div class="work-card-head">
          <el-radio v-model="keepId" :value="side.id">保留此作品</el-radio>
          <el-tag size="small" effect="plain">#{{ side.id }}</el-tag>
        </div>
        <h3>{{ side.work?.title || `作品 #${side.id}` }}</h3>
        <p v-if="side.work?.original_title" class="original-title">
          {{ side.work.original_title }}
        </p>
        <ul class="detail-list">
          <li v-for="(line, index) in describe(side.work)" :key="index">{{ line }}</li>
        </ul>
      </div>
    </div>

    <template #footer>
      <div class="footer">
        <span class="footer-hint">
          将删除作品 #{{ sourceId }}，数据合并至 #{{ targetId }}
        </span>
        <div class="spacer" />
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="merging" @click="confirm">确认合并</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type { DuplicateCandidate, Work } from '../types/api'

const props = defineProps<{
  modelValue: boolean
  candidate: DuplicateCandidate
  left: Work | null
  right: Work | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  merged: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const merging = ref(false)
const keepId = ref(props.candidate.work_id)

const sides = computed(() => [
  { id: props.candidate.work_id, work: props.left },
  { id: props.candidate.other_id, work: props.right },
])

const targetId = computed(() => keepId.value)
const sourceId = computed(() =>
  targetId.value === props.candidate.work_id
    ? props.candidate.other_id
    : props.candidate.work_id,
)

function votesOf(work: Work | null): number {
  if (!work) return 0
  return work.vndb_votecount ?? work.rating_count ?? work.bangumi_votecount ?? 0
}

function describe(work: Work | null): string[] {
  if (!work) return ['作品详情加载失败，可刷新后重试']
  const lines: string[] = [
    `来源：${work.source || '—'}`,
    `发售：${work.release_date || work.release_year || '—'}`,
    `评分：${work.rating ?? work.vndb_rating ?? work.bangumi_rating ?? '—'}`,
    `投票数：${votesOf(work)}`,
  ]
  if (work.tags?.length) lines.push(`标签：${work.tags.slice(0, 6).map((tag) => tag.name).join('、')}`)
  if (work.companies?.length) lines.push(`开发商：${work.companies.slice(0, 4).join('、')}`)
  return lines
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    keepId.value = votesOf(props.right) > votesOf(props.left)
      ? props.candidate.other_id
      : props.candidate.work_id
  },
)

async function confirm() {
  merging.value = true
  try {
    const result = await api.mergeWorks(sourceId.value, targetId.value)
    const moved = Object.values(result.moved).reduce((sum, value) => sum + value, 0)
    ElMessage.success(`合并完成，共迁移 ${moved} 条关联数据`)
    emit('merged')
    visible.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '合并失败')
  } finally {
    merging.value = false
  }
}
</script>

<style scoped>
.merge-intro {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f6f4fd;
  margin-bottom: 14px;
}

.merge-intro p {
  margin: 0 0 8px;
  font-size: 14px;
}

.merge-intro strong {
  color: #6f57d9;
}

.reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.keep-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #8a8fa3;
  line-height: 1.7;
}

.keep-hint strong {
  color: #6f57d9;
}

.choice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.work-card {
  border: 1px solid rgba(31, 35, 64, 0.1);
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.work-card:hover {
  border-color: #b9adf0;
}

.work-card.selected {
  border-color: #6f57d9;
  box-shadow: 0 0 0 2px rgba(111, 87, 217, 0.12);
}

.work-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.work-card h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.original-title {
  margin: 0 0 8px;
  color: #8a8fa3;
  font-size: 12px;
}

.detail-list {
  margin: 0;
  padding: 0;
  list-style: none;
  color: #8a8fa3;
  font-size: 12px;
  line-height: 1.8;
}

.detail-list li {
  overflow-wrap: anywhere;
}

.footer {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.footer-hint {
  color: #9a9fb0;
  font-size: 12px;
}

.spacer {
  flex: 1;
}

@media (max-width: 640px) {
  .choice-grid {
    grid-template-columns: 1fr;
  }
}
</style>
