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
        @click="showLoginModal = true" />
      <UColorModeButton />
    </template>
    <template #body>
      <UButton
        class="mt-4"
        icon="i-lucide-log-in"
        label="Войти"
        variant="subtle"
        block
        @click="showLoginModal = true" />
    </template>
  </UHeader>
  <!-- Один модальный компонент для обеих кнопок -->
  <UModal v-model:open="showLoginModal" title="Логин">
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
const USE_MOCK_LOGIN = false

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

const rawMock = `{
    "id": 359107176,
    "first_name": "М",
    "last_name": "С",
    "username": "chernyakoff",
    "photo_url": "https://t.me/i/userpic/320/E5CF1DXAc92hvxFoNm0Z4y4Z4ycjpk6DqbKdvmjyVyw.jpg",
    "auth_date": 1761654200,
    "hash": "6c6627cd20adb2efd9ab4338c06e6d01cae7ec247dca8b8e2fcf0098d6b1c949"
}`

function parseUserLogin (raw: string): UserLoginIn {
  const data = JSON.parse(raw)
  return {
    id: data.id,
    authDate: data.auth_date,
    hash: data.hash,
    firstName: data.first_name ?? null,
    lastName: data.last_name ?? null,
    username: data.username ?? null,
    photoUrl: data.photo_url ?? null,
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
      if (USE_MOCK_LOGIN) {
        // эмулируем "нажатие" на Telegram login
        const user = parseUserLogin(rawMock)
        console.log('🔧 Using mock Telegram login:', user)
        login(user)
          .then(() => {
            showLoginModal.value = false
          })
          .catch((err) => console.error('Mock login failed', err))
      } else {
        loadTelegramWidget()
      }
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
