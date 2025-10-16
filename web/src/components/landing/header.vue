<template>
  <UHeader>
    <template #left>
      <RouterLink to="/">
        <Logo />
      </RouterLink>
    </template>
    <template #right>
      <UButton
        icon="i-lucide-log-in"
        variant="subtle"
        class="hidden lg:block"
        @click="showLoginModal = true"
      />
      <UColorModeButton />
    </template>
    <template #body>
      <UButton
        class="mt-4"
        icon="i-lucide-log-in"
        label="Войти"
        variant="subtle"
        block
        @click="showLoginModal = true"
      />
    </template>
  </UHeader>

  <!-- Один модальный компонент для обеих кнопок -->
  <UModal v-model="showLoginModal" title="Логин">
    <template #body>
      <div class="tab-panel">
        <div id="telegram-login-container" class="flex justify-center my-4"></div>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Logo from '@/components/shared/logo.vue'
import { useAuth } from '@/composables/use-auth'
import type { UserLoginIn } from '@/types/openapi'

const { login } = useAuth()
const showLoginModal = ref(false)

const TELEGRAM_BOT_USERNAME = import.meta.env.BOT_NAME

interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}

declare global {
  interface Window {
    onTelegramAuth: (user: TelegramUser) => void
  }
}

onMounted(() => {
  window.onTelegramAuth = (user: TelegramUser) => {
    const telegramUser: UserLoginIn = {
      id: user.id,
      firstName: user.first_name,
      lastName: user.last_name || '',
      username: user.username || '',
      photoUrl: user.photo_url || '',
      authDate: user.auth_date,
      hash: user.hash,
    }

    login(telegramUser)
      .then(() => {
        showLoginModal.value = false
      })
      .catch((error) => {
        console.error('Login failed:', error)
      })
  }
})

watch(showLoginModal, (isOpen) => {
  if (isOpen) {
    setTimeout(() => {
      loadTelegramWidget()
    }, 100)
  }
})

const loadTelegramWidget = () => {
  const container = document.getElementById('telegram-login-container')
  if (!container) return

  container.innerHTML = ''

  const script = document.createElement('script')
  script.src = 'https://telegram.org/js/telegram-widget.js?22'
  script.setAttribute('data-telegram-login', TELEGRAM_BOT_USERNAME)
  script.setAttribute('data-size', 'large')
  script.setAttribute('data-onauth', 'onTelegramAuth(user)')
  script.setAttribute('data-request-access', 'write')
  script.async = true

  container.appendChild(script)
}
</script>
