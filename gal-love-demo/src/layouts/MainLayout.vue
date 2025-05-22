<template>
  <el-container class="layout-container">
    <el-header>
      <el-menu
        :router="true"
        mode="horizontal"
        :ellipsis="false"
        class="nav-menu"
      >
        <el-menu-item index="/">
          <el-icon><home-filled /></el-icon>
          首页
        </el-menu-item>
        <el-menu-item index="/games">
          <el-icon><list /></el-icon>
          游戏列表
        </el-menu-item>
        <div class="flex-grow" />
        <template v-if="!isLoggedIn">
          <el-menu-item index="/login">
            <el-icon><user /></el-icon>
            登录
          </el-menu-item>
          <el-menu-item index="/register">
            注册
          </el-menu-item>
        </template>
        <template v-else>
          <el-sub-menu index="user">
            <template #title>
              <el-icon><user /></el-icon>
              {{ username }}
            </template>
            <el-menu-item index="/profile">个人中心</el-menu-item>
            <el-menu-item @click="handleLogout">退出登录</el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-header>
    <el-main>
      <slot />
    </el-main>
    <el-footer>
      <p>&copy; 2025 Gal Love. All rights reserved.</p>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { HomeFilled, List, User } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const isLoggedIn = computed(() => userStore.isLoggedIn)
const username = computed(() => userStore.userInfo?.username || '用户')

const handleLogout = () => {
  if (userStore.logout) {
    userStore.logout()
    ElMessage.success('已退出登录')
    window.location.href = '/'
  }
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.el-header {
  padding: 0;
  height: auto;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.nav-menu {
  width: 100%;
  border-bottom: none;
}

.flex-grow {
  flex-grow: 1;
}

.el-main {
  flex: 1;
  padding: 20px;
  background-color: #f5f7fa;
}

.el-footer {
  text-align: center;
  padding: 20px;
  color: #666;
  background-color: #fff;
  border-top: 1px solid #eee;
}
</style>
