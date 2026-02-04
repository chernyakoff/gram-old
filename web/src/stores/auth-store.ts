import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/use-api'
import type {
  ImpersonateIn,
  ImpersonateOut,
  UserLoginIn,
  UserLoginOut,
  UserMeOut,
} from '@/types/openapi'


export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserMeOut | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const isAuthenticated = computed(() => !!accessToken.value)
  const isImpersonated = computed(() => user.value?.impersonated ?? false)

  
  const { api } = useApi()
  async function login(user: UserLoginIn) {

    const inviteRefCode = localStorage.getItem('inviteRefCode')
    
    if (inviteRefCode) {
      user.inviteRefCode = inviteRefCode
    }
    
  
    const data = await api<UserLoginOut>('auth', {
      method: 'POST',
      body: user,
    })
    
    accessToken.value = data.accessToken
    localStorage.setItem('accessToken', data.accessToken)
    
    localStorage.removeItem('inviteRefCode')
    await fetchUser()
    startBalancePolling()
  }

  async function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('accessToken')
    stopBalancePolling()
    try {
      await api('auth/logout', { method: 'POST' })
    } catch {
      // ignore errors
    }
  }

  async function refreshTokens() {
    try {
      const data = await api<UserLoginOut>('auth/refresh', {
        method: 'POST',
      })
      accessToken.value = data.accessToken
      localStorage.setItem('accessToken', data.accessToken)
      return true
    } catch {
      logout()
      return false
    }
  }

  async function fetchUser() {
    const me = await api<UserMeOut>('auth/me')
    user.value = me
  }

  async function impersonate(data: ImpersonateIn) {
    const result = await api<ImpersonateOut>('admin/impersonate', {
      method: 'POST',
      body: data,
    })
    accessToken.value = result.access
    localStorage.setItem('accessToken', result.access)
    await fetchUser()
  }

  async function stopImpersonate() {
    await api('admin/stop-impersonate', { method: 'POST' })
    // После остановки имперсонации нужно обновить токены
    await refreshTokens()
    await fetchUser()
  }

  let balanceInterval: number | null = null

  function startBalancePolling() {
    if (balanceInterval) return

    balanceInterval = window.setInterval(() => {
      if (accessToken.value && document.visibilityState === 'visible') {
        fetchUser()
      }
    }, 30_000)
  }

  function stopBalancePolling() {
    if (balanceInterval) {
      clearInterval(balanceInterval)
      balanceInterval = null
    }
  }

  if (accessToken.value) {
    startBalancePolling()
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    isImpersonated,

    login,
    logout,
    refreshTokens,
    fetchUser,
    impersonate,
    stopImpersonate,
  }
})
