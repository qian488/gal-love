<template>
  <el-dialog
    v-model="visible"
    :title="work ? `记录《${work.title}》` : '记录游戏'"
    width="min(520px, 92vw)"
    destroy-on-close
  >
    <div v-if="work" class="entry-head">
      <div class="entry-cover">
        <CoverImage :src="work.cover_url || undefined" :title="work.title" />
      </div>
      <div class="entry-head-info">
        <h3>{{ work.title }}</h3>
        <p v-if="zhAlias" class="alias">{{ zhAlias }}</p>
      </div>
    </div>

    <el-form v-if="work" label-width="72px" label-position="left">
      <el-form-item label="状态">
        <el-radio-group v-model="form.status">
          <el-radio-button
            v-for="(label, value) in entryStatusLabels"
            :key="value"
            :value="value"
          >
            {{ label }}
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="我的评分">
        <div class="rating-row">
          <el-rate v-model="form.rating" :max="10" allow-half />
          <span class="rating-text">
            {{ form.rating ? `${form.rating} / 10` : '暂不评分' }}
          </span>
        </div>
      </el-form-item>

      <el-form-item label="特别喜欢">
        <el-switch v-model="form.favorite" />
        <span class="hint">收藏会加强口味画像中的权重</span>
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.notes"
          type="textarea"
          :rows="4"
          maxlength="1000"
          show-word-limit
          placeholder="记下喜欢的路线、角色或想玩的原因…"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="footer">
        <el-button
          v-if="hasEntry"
          type="danger"
          plain
          :loading="removing"
          @click="removeExisting"
        >
          从游戏库移除
        </el-button>
        <div class="spacer" />
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { entryStatusLabels } from '../api'
import CoverImage from './CoverImage.vue'
import { useCatalogStore } from '../store/game'
import type { EntryStatus, Work } from '../types/api'

const props = defineProps<{
  modelValue: boolean
  work: Work | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const store = useCatalogStore()
const saving = ref(false)
const removing = ref(false)

const zhAlias = computed(() => {
  const title = (props.work?.titles ?? []).find((item) => item.lang.toLowerCase().startsWith('zh'))
  return title && title.title !== props.work?.title ? title.title : ''
})

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const form = reactive<{
  status: EntryStatus
  rating: number
  favorite: boolean
  notes: string
}>({
  status: 'want',
  rating: 0,
  favorite: false,
  notes: '',
})

const hasEntry = computed(() => (props.work ? Boolean(store.entryFor(props.work.id)) : false))

watch(
  () => [props.modelValue, props.work?.id] as const,
  ([open, workId]) => {
    if (!open || !workId) return
    const entry = store.entryFor(workId)
    form.status = entry?.status ?? 'want'
    form.rating = entry?.rating ?? 0
    form.favorite = entry?.favorite ?? false
    form.notes = entry?.notes ?? ''
  },
  { immediate: true },
)

async function save() {
  if (!props.work) return
  saving.value = true
  try {
    await store.saveEntry(props.work.id, {
      status: form.status,
      rating: form.rating > 0 ? form.rating : null,
      favorite: form.favorite,
      notes: form.notes.trim() || null,
    })
    ElMessage.success('已记录到我的游戏库')
    emit('saved')
    visible.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeExisting() {
  if (!props.work) return
  try {
    await ElMessageBox.confirm('确定从游戏库中移除这条记录吗？', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  removing.value = true
  try {
    await store.removeEntry(props.work.id)
    ElMessage.success('已从游戏库移除')
    emit('saved')
    visible.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '移除失败')
  } finally {
    removing.value = false
  }
}
</script>

<style scoped>
.entry-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.entry-cover {
  width: 64px;
  flex: none;
  border-radius: 8px;
  overflow: hidden;
  --cover-placeholder-size: 1.6rem;
}

.entry-head-info h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.4;
}

.entry-head-info .alias {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9a8fd0;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rating-text {
  color: #8a8fa3;
  font-size: 13px;
}

.hint {
  margin-left: 12px;
  color: #9a9fb0;
  font-size: 12px;
}

.footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spacer {
  flex: 1;
}
</style>
