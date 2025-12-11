// src/composables/useAuth.ts
import { toRefs, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'

export function useAuth() {
  const auth = useAuthStore()
  const router = useRouter()

  const { user, isAuthenticated, accessToken, isImpersonated } = toRefs(auth)

  // Автоматический редирект при изменении user
  watch(
    user,
    (newUser) => {
      if (newUser) {
        if (newUser.hasLicense) {
          if (router.currentRoute.value.name !== 'app') {
            router.push({ name: 'app' })
          }
        } else {
          if (router.currentRoute.value.name !== 'license') {
            router.push({ name: 'license' })
          }
        }
      } else {
        if (router.currentRoute.value.name !== 'main') {
          router.push({ name: 'main' })
        }
      }
    },
    { immediate: false }, // не срабатывает при первой инициализации
  )

  return {
    user,
    isAuthenticated,
    isImpersonated,
    accessToken,
    login: auth.login,
    logout: auth.logout,
    refresh: auth.refreshTokens,
    fetchUser: auth.fetchUser,
    impersonate: auth.impersonate,
    stopImpersonate: auth.stopImpersonate,
  }
}
