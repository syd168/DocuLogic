import { createRouter, createWebHistory } from 'vue-router'
import http from '@/api/http'

const routes = [
  { path: '/', name: 'landing', component: () => import('@/views/Landing.vue') },
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('@/views/Register.vue') },
  { path: '/forgot', name: 'forgot', component: () => import('@/views/Forgot.vue') },
  {
    path: '/app',
    name: 'workspace',
    component: () => import('@/views/Workspace.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  if (!to.meta.requiresAuth) {
    next()
    return
  }
  try {
    const { data } = await http.get('/api/auth/me')
    if (data && data.username) {
      next()
      return
    }
  } catch (e) {
    // 未登录是正常情况，静默处理，不显示错误日志
    if (e.response?.status !== 401) {
      console.error('路由守卫认证检查失败:', e.message)
    }
  }
  next({ path: '/login', query: { next: to.fullPath } })
})

export default router
