// src/composables/useAuth.ts
import { toRefs, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'

export function useAuth() {
  const auth = useAuthStore()
  const router = useRouter()

  const { user, isAuthenticated, accessToken, isImpersonated } = toRefs(auth)

  watch(
    () => user.value?.id, // смотрим только идентификатор
    (id, oldId) => {
      // редирект только при смене пользователя
      if (!id) {
        if (router.currentRoute.value.name !== 'main') {
          router.push({ name: 'main' })
        }
      } else if (!oldId) {
        // новый логин
        if (user.value?.hasLicense) {
          router.push({ name: 'app' })
        } else {
          router.push({ name: 'license' })
        }
      }
    },
    { immediate: false },
  )

  watch(
    () => user.value?.hasLicense,
    (hasLicense, oldHasLicense) => {
      // Если лицензия появилась (была false/undefined, стала true)
      if (hasLicense && !oldHasLicense && user.value?.id) {
        // Редирект только если мы на странице license
        if (router.currentRoute.value.name === 'license') {
          router.push({ name: 'app' })
        }
      }
    },
    { immediate: false },
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
