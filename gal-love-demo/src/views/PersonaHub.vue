<template>
  <div class="persona-hub">
    <header class="hub-head">
      <span class="eyebrow">PERSONA</span>
      <h1>画像测试</h1>
    </header>

    <div v-if="loading" class="grid">
      <div v-for="n in 6" :key="n" class="skeleton-card">
        <el-skeleton animated :rows="3" />
      </div>
    </div>

    <template v-else-if="groups.length">
      <section v-for="group in groups" :key="group.key" class="group">
        <h2>{{ group.title }}</h2>
        <div class="grid">
          <button
            v-for="provider in group.items"
            :key="provider.key"
            type="button"
            class="provider-card"
            @click="openProvider(provider)"
          >
            <div class="card-top">
              <h3 class="card-title">{{ provider.title }}</h3>
              <span v-if="provider.completed" class="done-tag">
                {{ provider.code || '已完成' }}
              </span>
            </div>

            <p v-if="provider.subtitle" class="card-subtitle">{{ provider.subtitle }}</p>

            <div class="card-foot">
              <span class="meta">{{ metaText(provider) }}</span>
              <el-icon class="go"><ArrowRight /></el-icon>
            </div>

            <p v-if="provider.notice" class="notice">{{ provider.notice }}</p>
          </button>
        </div>
      </section>
    </template>

    <el-empty v-else description="暂时没有可用的测试" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { api } from '../api'
import type { PersonaGroup, PersonaProviderInfo } from '../types/api'

interface ProviderGroup {
  key: PersonaGroup
  title: string
  items: PersonaProviderInfo[]
}

const GROUP_TITLES: Record<PersonaGroup, string> = {
  quick: '快速建立',
  play: '玩法',
  fun: '趣味',
  serious: '认真',
  other: '其他',
}

const GROUP_ORDER: PersonaGroup[] = ['quick', 'play', 'fun', 'serious', 'other']

const router = useRouter()
const loading = ref(true)
const providers = ref<PersonaProviderInfo[]>([])

const groups = computed<ProviderGroup[]>(() =>
  GROUP_ORDER.map((key) => ({
    key,
    title: GROUP_TITLES[key],
    items: providers.value.filter((provider) => provider.group === key),
  })).filter((group) => group.items.length > 0),
)

function metaText(provider: PersonaProviderInfo): string {
  const parts: string[] = []
  if (provider.question_count > 0) parts.push(`${provider.question_count} 题`)
  if (provider.estimated_minutes > 0) parts.push(`约 ${provider.estimated_minutes} 分钟`)
  return parts.join(' · ')
}

function openProvider(provider: PersonaProviderInfo) {
  if (provider.kind === 'pairwise') {
    router.push('/persona/pairwise')
    return
  }
  if (provider.kind === 'draw') {
    router.push('/persona/tarot')
    return
  }
  router.push(`/persona/${provider.key}`)
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await api.personaProviders()
    providers.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '测试列表加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.persona-hub {
  max-width: 1000px;
  margin: 0 auto;
  padding: 36px 24px 56px;
}

.hub-head {
  margin-bottom: 28px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #9a8fd0;
}

.hub-head h1 {
  margin: 8px 0 0;
  font-size: 30px;
  color: #2f274a;
}

.group + .group {
  margin-top: 30px;
}

.group h2 {
  margin: 0 0 14px;
  font-size: 18px;
  color: #2f274a;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.provider-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 20px;
  text-align: left;
  font: inherit;
  color: inherit;
  background: #fff;
  border: 1px solid rgba(31, 35, 64, 0.06);
  border-radius: 16px;
  box-shadow: 0 10px 28px rgba(93, 68, 168, 0.06);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.provider-card:hover {
  transform: translateY(-3px);
  border-color: #c7bcf0;
  box-shadow: 0 16px 36px rgba(93, 68, 168, 0.12);
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.card-title {
  margin: 0;
  font-size: 16px;
  color: #2f274a;
}

.done-tag {
  flex-shrink: 0;
  max-width: 60%;
  padding: 2px 10px;
  overflow: hidden;
  font-size: 11px;
  line-height: 18px;
  color: #5a44c4;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #f1eefd;
  border-radius: 999px;
}

.card-subtitle {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #8a8fa3;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.meta {
  font-size: 12px;
  font-weight: 600;
  color: #7c6fae;
}

.go {
  color: #b7a9e6;
}

.notice {
  margin: 0;
  font-size: 12px;
  color: #a09aae;
}

.skeleton-card {
  padding: 20px;
  background: #fff;
  border: 1px solid rgba(31, 35, 64, 0.06);
  border-radius: 16px;
}

@media (max-width: 560px) {
  .persona-hub {
    padding: 20px 14px 40px;
  }

  .hub-head h1 {
    font-size: 24px;
  }

  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
