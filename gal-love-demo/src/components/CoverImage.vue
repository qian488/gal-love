<template>
  <div class="cover-image" :style="rootStyle">
    <img
      v-if="src && !imageError && displaySrc"
      :src="displaySrc"
      :alt="alt ?? title"
      class="cover-image__img"
      loading="lazy"
      referrerpolicy="no-referrer"
      @error="onImageError"
    />
    <div v-else class="cover-image__placeholder" role="img" :aria-label="alt ?? title">
      <span>{{ title.slice(0, 1) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    src?: string
    title: string
    ratio?: string
    alt?: string
  }>(),
  { ratio: '3 / 4' },
)

const rootStyle = computed(() => ({ aspectRatio: props.ratio }))
const displaySrc = ref(props.src ?? '')
const imageError = ref(false)

let generation = 0
let objectUrl: string | null = null
let disposed = false

function revokeObjectUrl() {
  if (objectUrl) {
    try {
      URL.revokeObjectURL(objectUrl)
    } catch {
      // 某些环境（如 SSR / 隐私模式）可能没有 revokeObjectURL
    }
    objectUrl = null
  }
}

function onImageError() {
  imageError.value = true
}

function canCache(src: string): boolean {
  return Boolean(src) && !/^(data|blob):/i.test(src)
}

watch(
  () => props.src,
  (next) => {
    generation += 1
    revokeObjectUrl()
    imageError.value = false
    displaySrc.value = next ?? ''
    if (next) void loadFromCache(next, generation)
  },
)

if (props.src) void loadFromCache(props.src, generation)

onBeforeUnmount(() => {
  disposed = true
  generation += 1
  revokeObjectUrl()
})

async function loadFromCache(src: string, gen: number) {
  if (!canCache(src)) return
  const blob = await getCachedBlob(src)
  if (disposed || gen !== generation) return

  if (!blob) {
    void warmCache(src, gen)
    return
  }

  try {
    if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') return
    const url = URL.createObjectURL(blob)
    if (disposed || gen !== generation) {
      try {
        URL.revokeObjectURL(url)
      } catch {
        // ignore
      }
      return
    }
    revokeObjectUrl()
    objectUrl = url
    displaySrc.value = url
  } catch {
    // ObjectURL 创建失败时继续使用原始 URL
  }
}

async function warmCache(src: string, gen: number) {
  if (typeof fetch !== 'function') return
  try {
    const response = await fetch(src, { mode: 'cors' })
    if (!response.ok) return
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType && !contentType.toLowerCase().startsWith('image/')) return
    const blob = await response.blob()
    if (disposed || gen !== generation) return
    await saveCachedBlob(src, blob)
  } catch {
    // 跨域 / 离线 / 无 CORS 头时静默失败，直接使用原图 URL
  }
}

const DB_NAME = 'gal-love-cover-cache'
const STORE_NAME = 'covers'
const DB_VERSION = 1
let dbPromise: Promise<IDBDatabase | null> | null = null

function getDb(): Promise<IDBDatabase | null> {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve) => {
    if (typeof indexedDB === 'undefined') {
      resolve(null)
      return
    }
    let request: IDBOpenDBRequest
    try {
      request = indexedDB.open(DB_NAME, DB_VERSION)
    } catch {
      resolve(null)
      return
    }
    request.onupgradeneeded = () => {
      try {
        const db = request.result
        if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME)
      } catch {
        // ignore
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => resolve(null)
    request.onblocked = () => resolve(null)
  })
  return dbPromise
}

async function getCachedBlob(key: string): Promise<Blob | null> {
  const db = await getDb()
  if (!db) return null
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const request = tx.objectStore(STORE_NAME).get(key)
      request.onsuccess = () => {
        const result = request.result
        resolve(typeof Blob !== 'undefined' && result instanceof Blob ? result : null)
      }
      request.onerror = () => resolve(null)
      tx.onerror = () => resolve(null)
      tx.onabort = () => resolve(null)
    } catch {
      resolve(null)
    }
  })
}

async function saveCachedBlob(key: string, blob: Blob): Promise<void> {
  const db = await getDb()
  if (!db) return
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put(blob, key)
      tx.oncomplete = () => resolve()
      tx.onerror = () => resolve()
      tx.onabort = () => resolve()
    } catch {
      resolve()
    }
  })
}
</script>

<style scoped>
.cover-image {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: linear-gradient(135deg, #ddd8ff, #f4e7ff);
}

.cover-image__img,
.cover-image__placeholder {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-image__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(88, 64, 180, 0.5);
  font-size: var(--cover-placeholder-size, 3rem);
  font-weight: 700;
}
</style>
