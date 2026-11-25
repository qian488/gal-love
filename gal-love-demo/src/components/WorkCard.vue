<template>
  <article class="work-card" @click="openWork">
    <div class="cover-wrap">
      <CoverImage :src="work.cover_url || undefined" :title="work.title" />
      <span v-if="work.nsfw" class="nsfw-badge">R18</span>
      <span v-if="ratingText" class="rating-badge">{{ ratingText }}</span>
    </div>

    <div class="body">
      <h3 class="title" :title="work.title">{{ work.title }}</h3>
      <p v-if="zhAlias" class="alias" :title="zhAlias">{{ zhAlias }}</p>
      <p v-if="metaText" class="meta">{{ metaText }}</p>

      <p v-if="props.reason && work.reason" class="reason">
        {{ work.reason }}
      </p>
      <p v-if="props.reason && sharedTagsText" class="shared-tags">
        共同标签：{{ sharedTagsText }}
      </p>

      <div class="tags">
        <el-tag
          v-for="tag in visibleTags"
          :key="tag.name"
          size="small"
          effect="plain"
          class="tag"
        >
          {{ tag.name }}
        </el-tag>
      </div>

      <slot name="actions" />
      <slot />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import CoverImage from './CoverImage.vue'
import type { Work } from '../types/api'

const props = withDefaults(
  defineProps<{
    work: Work
    reason?: boolean
    tagLimit?: number
  }>(),
  { reason: false, tagLimit: 4 },
)

const router = useRouter()

const zhAlias = computed(() => {
  const title = (props.work.titles ?? []).find((item) => item.lang.toLowerCase().startsWith('zh'))
  return title && title.title !== props.work.title ? title.title : ''
})

const sharedTagsText = computed(() => (props.work.shared_tags ?? []).slice(0, 6).join(' · '))

const ratingText = computed(() => {
  if (props.work.score !== undefined) return `${Math.round(props.work.score * 100)} 分匹配`
  if (typeof props.work.rating === 'number') return props.work.rating.toFixed(1)
  return ''
})

const metaText = computed(() => {
  const parts: string[] = []
  if (props.work.release_year) parts.push(String(props.work.release_year))
  if (props.work.companies.length) parts.push(props.work.companies[0])
  if (props.work.length_minutes) {
    const hours = Math.round(props.work.length_minutes / 60)
    parts.push(hours >= 1 ? `约 ${hours} 小时` : `${props.work.length_minutes} 分钟`)
  }
  return parts.join(' · ')
})

const visibleTags = computed(() => props.work.tags.slice(0, props.tagLimit))

function openWork() {
  router.push({ name: 'WorkDetail', params: { id: props.work.id } })
}
</script>

<style scoped>
.work-card {
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(31, 35, 64, 0.06);
  border: 1px solid rgba(31, 35, 64, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.work-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 36px rgba(31, 35, 64, 0.12);
}

.cover-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  background: linear-gradient(135deg, #ddd8ff, #f4e7ff);
  --cover-placeholder-size: 3rem;
}

.nsfw-badge,
.rating-badge {
  position: absolute;
  top: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 18px;
  backdrop-filter: blur(8px);
}

.nsfw-badge {
  left: 10px;
  background: rgba(190, 40, 60, 0.88);
  color: #fff;
}

.rating-badge {
  right: 10px;
  background: rgba(20, 20, 30, 0.72);
  color: #fff;
}

.body {
  padding: 14px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.title {
  margin: 0;
  font-size: 16px;
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.alias {
  margin: -2px 0 0;
  font-size: 12px;
  color: #9a8fd0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  margin: 0;
  font-size: 12px;
  color: #8a8fa3;
}

.reason {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #5b5478;
  background: #f6f3ff;
  border-radius: 8px;
  padding: 8px 10px;
}

.shared-tags {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #7a70a8;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  border-radius: 999px;
}
</style>
