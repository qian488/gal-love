<template>
  <div class="detail-page">
    <el-button text class="back" @click="router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="loading" v-loading="true" class="loading-block" />

    <el-result
      v-else-if="!work"
      icon="warning"
      title="作品不存在"
      sub-title="它可能已被移除，或者链接有误。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/explore')">去探索</el-button>
      </template>
    </el-result>

    <template v-else>
      <section class="hero-card">
        <div class="cover-wrap">
          <CoverImage :src="work.cover_url || undefined" :title="work.title" />
        </div>

        <div class="info">
          <div class="title-row">
            <div>
              <h1>{{ work.title }}</h1>
              <dl v-if="allTitles.length" class="title-list">
                <template v-for="group in allTitles" :key="group.label">
                  <dt>{{ group.label }}</dt>
                  <dd>{{ group.values.join(' · ') }}</dd>
                </template>
              </dl>
            </div>
            <el-tag v-if="work.nsfw" type="danger" effect="dark" round>R18</el-tag>
          </div>

          <div class="rating-row">
            <template v-if="typeof work.rating === 'number'">
              <el-rate
                :model-value="work.rating / 2"
                disabled
                allow-half
                show-score
                score-template=""
              />
              <strong class="rating-value">{{ work.rating.toFixed(2) }}</strong>
              <span class="rating-source">
                {{ ratingSource }}
                <template v-if="work.rating_count"> · {{ work.rating_count }} 人评价</template>
              </span>
            </template>
            <span v-else class="rating-source">暂无外部评分</span>
          </div>

          <div class="meta-grid">
            <div>
              <span>发售</span>
              <strong>{{ work.release_date || '未知' }}</strong>
            </div>
            <div>
              <span>时长</span>
              <strong>{{ lengthText }}</strong>
            </div>
            <div>
              <span>开发商</span>
              <strong>{{ work.companies.join(' / ') || '未知' }}</strong>
            </div>
            <div>
              <span>平台</span>
              <strong>{{ work.platforms.slice(0, 6).join(' / ') || '未知' }}</strong>
            </div>
          </div>

          <div class="tags">
            <el-tag
              v-for="tag in work.tags.slice(0, 16)"
              :key="tag.name"
              size="small"
              effect="plain"
              round
            >
              {{ tag.name }}
            </el-tag>
          </div>

          <div class="actions">
            <el-button type="primary" @click="entryDialogVisible = true">
              <el-icon><EditPen /></el-icon>
              {{ work.entry ? '编辑我的记录' : '加入游戏库' }}
            </el-button>
            <el-button v-if="!work.entry" @click="notInterested">不感兴趣</el-button>
            <el-button v-if="externalUrl" tag="a" text type="primary" @click="openExternal">
              在来源站查看 <el-icon><TopRight /></el-icon>
            </el-button>
          </div>

          <div v-if="work.entry" class="my-entry">
            <el-tag :color="entryStatusColors[work.entry.status]" effect="dark" round>
              {{ entryStatusLabels[work.entry.status] }}
            </el-tag>
            <span v-if="work.entry.rating">我的评分 {{ work.entry.rating }} / 10</span>
            <span v-if="work.entry.favorite">★ 特别喜欢</span>
            <span v-if="work.entry.notes" class="notes">{{ work.entry.notes }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2>作品简介</h2>
        <p v-if="description" class="description">{{ description }}</p>
        <el-empty v-else description="暂无简介" :image-size="72" />
      </section>

      <section v-if="externalLinks.length" class="panel">
        <h2>外部链接</h2>
        <div class="external-links">
          <a
            v-for="link in externalLinks"
            :key="link.key"
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="external-link"
          >
            {{ link.label }}
            <el-icon><TopRight /></el-icon>
          </a>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>相似作品</h2>
            <p>按标签内容、开发商、年代与时长综合计算。</p>
          </div>
        </div>
        <div v-loading="similarLoading" class="similar-grid">
          <WorkCard
            v-for="item in similar"
            :key="item.id"
            :work="item"
            :tag-limit="3"
          />
        </div>
        <el-empty
          v-if="!similarLoading && !similar.length"
          description="还没有足够的相似作品"
          :image-size="72"
        />
      </section>
    </template>

    <EntryDialog v-model="entryDialogVisible" :work="work" @saved="handleSaved" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, EditPen, TopRight } from '@element-plus/icons-vue'
import CoverImage from '../components/CoverImage.vue'
import EntryDialog from '../components/EntryDialog.vue'
import WorkCard from '../components/WorkCard.vue'
import { api, entryStatusColors, entryStatusLabels } from '../api'
import { useCatalogStore } from '../store/game'
import type { Work } from '../types/api'

const route = useRoute()
const router = useRouter()
const store = useCatalogStore()

const work = ref<Work | null>(null)
const similar = ref<Work[]>([])
const loading = ref(true)
const similarLoading = ref(false)
const entryDialogVisible = ref(false)

const description = computed(() => cleanDescription(work.value?.description))

interface TitleGroup {
  label: string
  values: string[]
}

const allTitles = computed<TitleGroup[]>(() => {
  const current = work.value
  if (!current) return []
  const titles = current.titles ?? []
  const isZh = (lang: string) => lang.toLowerCase().startsWith('zh')
  const isJa = (lang: string) => /^(ja|jp)/i.test(lang)
  const groups: TitleGroup[] = []

  const zh = titles.filter(
    (item) => item.title && item.title !== current.title && isZh(item.lang),
  )
  if (zh.length) groups.push({ label: '中文别名', values: zh.map((item) => item.title) })

  const jaValues = titles
    .filter(
      (item) =>
        item.title &&
        item.title !== current.title &&
        isJa(item.lang) &&
        !zh.some((entry) => entry.title === item.title),
    )
    .map((item) => item.title)
  if (
    current.original_title &&
    current.original_title !== current.title &&
    !jaValues.includes(current.original_title)
  ) {
    jaValues.unshift(current.original_title)
  }
  if (jaValues.length) groups.push({ label: '日文原名', values: jaValues })

  const romanized: string[] = []
  for (const item of titles) {
    if (item.latin && !romanized.includes(item.latin)) romanized.push(item.latin)
  }
  if (current.romanized_title && !romanized.includes(current.romanized_title)) {
    romanized.push(current.romanized_title)
  }
  if (romanized.length) groups.push({ label: '罗马音', values: romanized })

  const otherValues = titles
    .filter(
      (item) => item.title && item.title !== current.title && !isZh(item.lang) && !isJa(item.lang),
    )
    .map((item) => item.title)
    .filter((value, index, values) => values.indexOf(value) === index)
  if (otherValues.length) groups.push({ label: '其他标题', values: otherValues })

  return groups
})

const sourceLabels: Record<string, string> = {
  vndb: 'VNDB',
  bangumi: 'Bangumi',
}

const externalLinks = computed(() =>
  (work.value?.external_refs ?? [])
    .filter((ref) => Boolean(ref.url))
    .map((ref) => ({
      key: `${ref.source}:${ref.external_id}`,
      label: sourceLabels[ref.source.toLowerCase()] ?? ref.source,
      url: ref.url as string,
    })),
)

const lengthText = computed(() => {
  const minutes = work.value?.length_minutes
  if (!minutes) return '未知'
  const hours = Math.round((minutes / 60) * 10) / 10
  return `约 ${hours} 小时`
})

const ratingSource = computed(() => {
  if (typeof work.value?.vndb_rating === 'number') return 'VNDB'
  if (typeof work.value?.bangumi_rating === 'number') return 'Bangumi'
  return '综合'
})

const externalUrl = computed(() => {
  const refs = work.value?.external_refs ?? []
  return refs.find((item) => item.source === 'vndb')?.url ?? refs[0]?.url ?? ''
})

function cleanDescription(text?: string | null): string {
  if (!text) return ''
  return text
    .replace(/\[url=[^\]]*\]/gi, '')
    .replace(/\[\/url\]/gi, '')
    .replace(/\[spoiler\]/gi, '')
    .replace(/\[\/spoiler\]/gi, '')
    .replace(/\[[^\]]+\]/g, '')
    .replace(/\r/g, '')
    .trim()
}

async function load(id: number) {
  loading.value = true
  similar.value = []
  try {
    work.value = await api.work(id)
    similarLoading.value = true
    try {
      similar.value = (await api.similar(id, 8)).items
    } finally {
      similarLoading.value = false
    }
  } catch (error) {
    work.value = null
    ElMessage.error(error instanceof Error ? error.message : '加载作品失败')
  } finally {
    loading.value = false
  }
}

async function notInterested() {
  if (!work.value) return
  try {
    await ElMessageBox.confirm('标记为不感兴趣后，推荐会减少类似作品。', '不感兴趣', {
      confirmButtonText: '标记',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await api.feedback({ work_id: work.value.id, kind: 'not_interested' })
    ElMessage.success('已记录反馈')
    router.push('/')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  }
}

async function handleSaved() {
  if (!work.value) return
  const id = work.value.id
  try {
    work.value = await api.work(id)
    await store.fetchEntries()
  } catch {
    // 保存已成功，详情刷新失败不影响主流程
  }
}

function openExternal() {
  if (externalUrl.value) window.open(externalUrl.value, '_blank', 'noopener')
}

watch(
  () => Number(route.params.id),
  (id) => {
    if (Number.isFinite(id) && id > 0) load(id)
  },
  { immediate: true },
)
</script>

<style scoped>
.detail-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 28px 56px;
}

.back {
  margin-bottom: 12px;
  color: #6f678e;
}

.loading-block {
  min-height: 320px;
}

.hero-card {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 28px;
  background: #fff;
  border-radius: 20px;
  padding: 26px;
  border: 1px solid rgba(31, 35, 64, 0.06);
  box-shadow: 0 14px 40px rgba(31, 35, 64, 0.07);
}

.cover-wrap {
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(135deg, #ddd8ff, #f4e7ff);
  --cover-placeholder-size: 4rem;
}

.title-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.25;
}

.title-list {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 3px 10px;
  margin: 10px 0 0;
  font-size: 13px;
}

.title-list dt {
  color: #9a8fd0;
  white-space: nowrap;
}

.title-list dd {
  margin: 0;
  color: #8a8fa3;
  overflow-wrap: anywhere;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 0 18px;
}

.rating-value {
  font-size: 20px;
  color: #e6a23c;
}

.rating-source {
  font-size: 13px;
  color: #8a8fa3;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 24px;
  margin-bottom: 18px;
}

.meta-grid div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-grid span {
  font-size: 12px;
  color: #9a9fb0;
}

.meta-grid strong {
  font-size: 14px;
  font-weight: 500;
  color: #3a3550;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 18px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.my-entry {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f7f6fc;
  font-size: 13px;
  color: #5f5a78;
}

.my-entry .notes {
  flex-basis: 100%;
  color: #8a8fa3;
}

.panel {
  margin-top: 20px;
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  border: 1px solid rgba(31, 35, 64, 0.06);
}

.panel h2 {
  margin: 0 0 12px;
  font-size: 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-head p {
  margin: 4px 0 0;
  color: #8a8fa3;
  font-size: 13px;
}

.description {
  margin: 0;
  white-space: pre-line;
  color: #555066;
  line-height: 1.9;
}

.external-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.external-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f6f3ff;
  color: #6f57d9;
  font-size: 13px;
}

.external-link:hover {
  background: #ebe5ff;
}

.similar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 18px;
  min-height: 120px;
}

@media (max-width: 760px) {
  .detail-page {
    padding: 20px 16px 40px;
  }

  .hero-card {
    grid-template-columns: 1fr;
  }

  .cover-wrap {
    max-width: 240px;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
