import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'main', component: () => import('@/pages/main/IndexPage.vue') },
      { path: 'license', name: 'license', component: () => import('@/pages/main/LicensePage.vue') },
    ],
  },
  {
    path: '/app',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', name: 'app', component: () => import('@/pages/app/IndexPage.vue') },
      { path: 'accounts', component: () => import('@/pages/app/AccountsPage.vue') },
      { path: 'contacts', component: () => import('@/pages/app/ContactsPage.vue') },
      { path: 'proxies', component: () => import('@/pages/app/ProxiesPage.vue') },
      { path: 'jobs', component: () => import('@/pages/app/JobsPage.vue') },
      { path: 'projects', component: () => import('@/pages/app/ProjectsPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // если store ещё не знает пользователя, подтягиваем
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      await auth.logout()
    }
  }

  if (!auth.isAuthenticated && to.name !== 'main') {
    // не залогинен → на главную
    return next({ name: 'main' })
  }

  if (auth.isAuthenticated && to.name === 'main') {
    // залогинен → на дашборд или лицензию
    if (auth.user?.hasLicense) {
      return next({ name: 'app' })
    } else {
      return next({ name: 'license' })
    }
  }

  // проверка лицензии для защищённых страниц
  if (auth.isAuthenticated && !auth.user?.hasLicense && to.name === 'app') {
    return next({ name: 'license' })
  }

  next()
})
export default router
