<template>
  <UHeader>
    <template #left>
      <RouterLink to="/">
        <Logo />
      </RouterLink>
    </template>
    <template #right>
      <UButton
        @click="showLoginModal = true"
        icon="i-lucide-log-in"
        variant="subtle"
        class="hidden lg:block"
      />
      <UColorModeButton />
    </template>
    <template #body>
      <UButton
        @click="showLoginModal = true"
        class="mt-4"
        icon="i-lucide-log-in"
        label="Войти"
        variant="subtle"
        block
      />
    </template>
  </UHeader>

  <!-- Telegram Login Modal -->
  <Teleport to="body">
    <div
      v-if="showLoginModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showLoginModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold mb-4 text-center">Вход через Telegram</h3>
        <div id="telegram-login-container" class="flex justify-center my-4"></div>
        <button
          @click="showLoginModal = false"
          class="mt-4 w-full text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
        >
          Отмена
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Logo from '@/components/shared/logo.vue'
import { useAuth } from '@/composables/use-auth'
import type { UserLoginIn } from '@/types/openapi'

const { login } = useAuth()
const showLoginModal = ref(false)
const toast = useToast()

const TELEGRAM_BOT_USERNAME = import.meta.env.BOT_NAME

// Глобальный callback для Telegram Widget
declare global {
  interface Window {
    onTelegramAuth: (user: TelegramUser) => void
  }
}

onMounted(() => {
  // Определяем глобальный callback
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
        toast.add({
          title: 'Ошибка логина',
          description: error,
          color: 'error',
        })
      })
  }
})

// Загружаем виджет когда открывается модальное окно
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

  // Очищаем контейнер
  container.innerHTML = ''

  // Создаем script для Telegram Widget
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
