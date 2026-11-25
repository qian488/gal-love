import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/Home.vue'),
      meta: { title: '推荐' },
    },
    {
      path: '/taste-quiz',
      name: 'TasteQuiz',
      component: () => import('../views/TasteQuiz.vue'),
      meta: { title: '口味测试' },
    },
    {
      path: '/onboarding',
      name: 'Onboarding',
      component: () => import('../views/Onboarding.vue'),
      meta: { title: '冷启动引导' },
    },
    {
      path: '/explore',
      name: 'Explore',
      component: () => import('../views/Explore.vue'),
      meta: { title: '探索作品' },
    },
    {
      path: '/works/:id',
      name: 'WorkDetail',
      component: () => import('../views/WorkDetail.vue'),
      meta: { title: '作品详情' },
    },
    {
      path: '/library',
      name: 'Library',
      component: () => import('../views/Library.vue'),
      meta: { title: '我的游戏库' },
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/Settings.vue'),
      meta: { title: '设置与数据' },
    },
    {
      path: '/games',
      redirect: '/explore',
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/404.vue'),
      meta: { title: '页面未找到' },
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? '加载中'} · 代号G`
})

export default router
