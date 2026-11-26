<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <router-link to="/" class="brand">
          <span class="brand-mark">G</span>
          <span class="brand-name">代号G</span>
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
          <el-menu-item index="/persona">
            <el-icon><QuestionFilled /></el-icon>
            口味测试
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

      </div>
    </header>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Collection, Compass, HomeFilled, QuestionFilled, Setting } from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/persona') || route.path.startsWith('/taste-quiz')) return '/persona'
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
  min-width: 120px;
  color: inherit;
  text-decoration: none;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #2f274a;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6f57d9, #b06ab3);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 0.02em;
  box-shadow: 0 8px 20px rgba(111, 87, 217, 0.3);
}

.nav {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  border-bottom: none;
  background: transparent;
  scrollbar-width: none;
}

.nav::-webkit-scrollbar {
  display: none;
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

.app-main {
  flex: 1;
}

@media (max-width: 860px) {
  .topbar-inner {
    padding: 0 12px;
    gap: 8px;
  }

  .brand {
    min-width: 0;
  }

  .brand-name {
    display: none;
  }

  .nav :deep(.el-menu-item) {
    padding: 0 10px;
    margin: 0;
    white-space: nowrap;
  }

  .nav :deep(.el-icon) {
    margin-right: 2px;
  }
}
</style>
