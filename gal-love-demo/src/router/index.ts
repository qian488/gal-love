import { createRouter, createWebHistory } from 'vue-router'
import type { RouteLocationNormalized } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/games',
    name: 'Games',
    component: () => import('../views/Games.vue'),
    meta: { title: '游戏列表' }
  },
  {
    path: '/games/:id',
    name: 'GameDetail',
    component: () => import('../views/GameDetail.vue'),
    meta: { title: '游戏详情' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', guest: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: '个人中心', requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/404.vue'),
    meta: { title: '页面未找到' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to: RouteLocationNormalized, _from: RouteLocationNormalized, savedPosition: { left: number; top: number } | null) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

// 全局路由守卫
router.beforeEach(async (to: RouteLocationNormalized, _from: RouteLocationNormalized, next: (to?: any) => void) => {
  // 更新页面标题
  document.title = `${to.meta.title || '加载中'} - Galgame 推荐系统`
  
  const userStore = useUserStore()
  const isLoggedIn = userStore.isLoggedIn
  
  // 尝试恢复用户会话
  if (!isLoggedIn && localStorage.getItem('token')) {
    try {
      await userStore.initUserState()
    } catch (error) {
      // 如果恢复会话失败，清除token
      localStorage.removeItem('token')
      if (to.meta.requiresAuth) {
        next({ name: 'Login', query: { redirect: to.fullPath } })
        return
      }
    }
  }
  
  // 需要认证的路由
  if (to.meta.requiresAuth && !isLoggedIn) {
    ElMessage.warning('请先登录')
    next({ 
      name: 'Login',
      query: { redirect: to.fullPath }
    })
    return
  }
  
  // 已登录用户不能访问游客页面
  if (to.meta.guest && isLoggedIn) {
    next({ name: 'Home' })
    return
  }
  
  next()
})

export default router
