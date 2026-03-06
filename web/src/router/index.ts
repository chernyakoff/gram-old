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
      { path: 'calendar', component: () => import('@/views/dashboard/calendar.vue') },
      {
        path: 'project/:id',
        name: 'project',
        component: () => import('@/views/dashboard/project.vue'),
        props: true,
      },
    ],
  },

  {
    path: '/r/:code',
    name: 'ref',
    component: () => import('@/views/landing/index.vue'),
    beforeEnter: (to) => {
      const code = to.params.code as string


      // Сохраняем напрямую в localStorage (синхронно)
      localStorage.setItem('inviteRefCode', code)

      // Редирект на главную
      return { name: 'main' }
    },
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.name === 'ref') {
    return next()
  }

  const accessTokenFromQuery =
    typeof to.query.access_token === 'string' ? to.query.access_token : null
  if (accessTokenFromQuery) {
    auth.setAccessToken(accessTokenFromQuery)
    const { access_token: _ignored, ...restQuery } = to.query
    return next({
      path: to.path,
      query: restQuery,
      hash: to.hash,
      replace: true,
    })
  }

  // --------------------------
  // 2️⃣ ПОДТЯГИВАЕМ ПОЛЬЗОВАТЕЛЯ
  // --------------------------
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      await auth.logout()
    }
  }

  // --------------------------
  // 3️⃣ РЕДИРЕКТЫ ПО AUTH / ЛИЦЕНЗИИ
  // --------------------------
  if (!auth.isAuthenticated && to.name !== 'main') {
    return next({ name: 'main' })
  }

  if (auth.isAuthenticated && to.name === 'main') {
    if (auth.user?.hasLicense) {
      return next({ name: 'app' })
    } else {
      return next({ name: 'license' })
    }
  }

  if (auth.isAuthenticated && !auth.user?.hasLicense && to.path.startsWith('/app')) {
    // Allow admins to reach the admin panel even without a license, including while impersonating.
    // Security must be enforced on the API side; this only affects client routing.
    const isAdminRoute = to.path === '/app/admin' || to.path.startsWith('/app/admin/')
    const canReachAdmin =
      isAdminRoute && (auth.user?.role === 'ADMIN' || auth.user?.impersonated === true)

    if (!canReachAdmin) {
      return next({ name: 'license' })
    }
  }

  next()
})

export default router
