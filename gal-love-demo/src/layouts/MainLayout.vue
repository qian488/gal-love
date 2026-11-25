<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <router-link to="/" class="brand">
          <span class="brand-mark">GL</span>
          <span class="brand-copy">
            <strong>Gal Love</strong>
            <small>个人视觉小说推荐</small>
          </span>
        </router-link>

        <el-menu
          :default-active="activeMenu"
          :router="true"
          mode="horizontal"
          :ellipsis="false"
          class="nav"
        >
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            推荐
          </el-menu-item>
          <el-menu-item index="/explore">
            <el-icon><Compass /></el-icon>
            探索
          </el-menu-item>
          <el-menu-item index="/library">
            <el-icon><Collection /></el-icon>
            我的游戏
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            设置
          </el-menu-item>
        </el-menu>

        <div class="topbar-side">
          <el-tag size="small" round effect="plain">本地自用</el-tag>
          <el-link
            href="http://localhost:8000/docs"
            target="_blank"
            :underline="false"
            class="docs-link"
          >
            API
          </el-link>
        </div>
      </div>
    </header>

    <main class="app-main">
      <slot />
    </main>

    <footer class="app-footer">
      <span>Gal Love · 个人向视觉小说 / AVG 推荐系统</span>
      <span>数据来自 VNDB / Bangumi · 仅用于个人学习与自用</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Collection, Compass, HomeFilled, Setting } from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/explore') || route.path.startsWith('/works')) return '/explore'
  if (route.path.startsWith('/library')) return '/library'
  if (route.path.startsWith('/settings')) return '/settings'
  return '/'
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(31, 35, 64, 0.07);
}

.topbar-inner {
  max-width: 1220px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  height: 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 180px;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6f57d9, #b06ab3);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0.02em;
  box-shadow: 0 8px 20px rgba(111, 87, 217, 0.3);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-copy strong {
  font-size: 17px;
}

.brand-copy small {
  color: #9a9fb0;
  font-size: 11px;
}

.nav {
  flex: 1;
  border-bottom: none;
  background: transparent;
}

.nav :deep(.el-menu-item) {
  border-radius: 10px;
  margin: 0 4px;
  padding: 0 14px;
  height: 42px;
  line-height: 42px;
}

.nav :deep(.el-menu-item.is-active) {
  background: #f1eefd;
  font-weight: 600;
}

.topbar-side {
  display: flex;
  align-items: center;
  gap: 12px;
}

.docs-link {
  font-size: 13px;
  color: #8a8fa3;
}

.app-main {
  flex: 1;
}

.app-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  max-width: 1220px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
  color: #9a9fb0;
  font-size: 12px;
  border-top: 1px solid rgba(31, 35, 64, 0.06);
}

@media (max-width: 860px) {
  .brand-copy small,
  .topbar-side {
    display: none;
  }

  .topbar-inner {
    padding: 0 12px;
    gap: 8px;
  }

  .brand {
    min-width: auto;
  }

  .nav :deep(.el-menu-item) {
    padding: 0 10px;
    margin: 0;
  }

  .nav :deep(.el-icon) {
    margin-right: 2px;
  }
}

@media (max-width: 620px) {
  .brand-copy {
    display: none;
  }

  .app-footer {
    flex-direction: column;
    padding: 18px 16px;
  }
}
</style>
