import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth-store'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/landing/layout.vue'),
    children: [
      { path: '', name: 'main', component: () => import('@/views/landing/index.vue') },
      { path: 'license', name: 'license', component: () => import('@/views/landing/license.vue') },
    ],
  },
  {
    path: '/app',
    component: () => import('@/views/dashboard/layout.vue'),
    children: [
      { path: '', name: 'app', component: () => import('@/views/dashboard/index.vue') },
      { path: 'accounts', component: () => import('@/views/dashboard/accounts.vue') },
      { path: 'proxies', component: () => import('@/views/dashboard/proxies.vue') },
      { path: 'mailings', component: () => import('@/views/dashboard/mailings.vue') },
      { path: 'dialogs', component: () => import('@/views/dashboard/dialogs.vue') },
      { path: 'jobs', component: () => import('@/views/dashboard/jobs.vue') },
      { path: 'admin', component: () => import('@/views/dashboard/admin.vue') },
      { path: 'projects', component: () => import('@/views/dashboard/projects.vue') },
      { path: 'settings', component: () => import('@/views/dashboard/settings.vue') },
      {
        path: 'project/:id?',
        name: 'project-create',
        component: () => import('@/views/dashboard/project-create.vue'),
        props: true, // чтобы id сразу приходил как пропс
      },
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
