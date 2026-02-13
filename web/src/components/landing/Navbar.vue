<template>
  <nav :class="['fixed top-0 left-0 right-0 z-50 transition-all duration-300', navBackground]">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-20">
        <div class="flex-shrink-0 flex items-center gap-2 cursor-pointer" @click="scrollToTop">
          <div
            class="bg-gradient-to-br from-primary-500 to-accent-600 p-2 rounded-lg shadow-lg shadow-primary-500/20"
          >
            <Send class="h-6 w-6 text-white" />
          </div>
          <span class="font-bold text-xl tracking-tight text-white uppercase">Лидоруб</span>
        </div>

        <div class="hidden md:flex items-center gap-6">
          <div class="flex space-x-6">
            <a
              v-for="item in navItems"
              :key="item.label"
              :href="item.href"
              class="text-slate-300 hover:text-white font-medium transition-colors text-sm hover:drop-shadow-glow"
            >
              {{ item.label }}
            </a>
          </div>

          <div class="flex items-center gap-3 border-l border-slate-700 pl-6 h-8">
            <template v-if="!isAuthenticated">
              <UButton
                @click="showLoginModal = true"
                variant="link"
                color="neutral"
                size="md"
                class="gap-2"
              >
                <LogIn class="h-4 w-4" />
                Вход
              </UButton>
            </template>
            <template v-else>
              <UButton
                @click="goToCabinet"
                variant="link"
                color="neutral"
                size="md"
                class="gap-2"
              >
                Кабинет
              </UButton>
              <UButton
                v-if="isImpersonated"
                @click="onStopImpersonate"
                variant="link"
                color="neutral"
                size="md"
                class="gap-2"
              >
                Выйти из имперсонации
              </UButton>
              <UButton
                @click="onLogout"
                variant="link"
                color="neutral"
                size="md"
                class="gap-2"
              >
                Выйти
              </UButton>
            </template>

            <a href="https://t.me/Maksim_Belichenko" target="_blank" rel="noopener noreferrer">
              <Button
                size="sm"
                class="bg-gradient-to-r from-primary-700 to-accent-700 hover:from-primary-600 hover:to-accent-600 text-white border-none shadow-lg shadow-primary-900/50 font-extrabold tracking-wide"
              >
                Связаться в Telegram
              </Button>
            </a>
          </div>
        </div>

        <div class="md:hidden flex items-center">
          <button
            class="text-slate-300 hover:text-white focus:outline-none"
            @click="isOpen = !isOpen"
          >
            <X v-if="isOpen" class="h-6 w-6" />
            <Menu v-else class="h-6 w-6" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="isOpen" class="md:hidden bg-slate-900 border-b border-slate-800 absolute w-full">
      <div class="px-4 pt-2 pb-6 space-y-2">
        <a
          v-for="item in navItems"
          :key="item.label"
          :href="item.href"
          class="block px-3 py-3 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
          @click="isOpen = false"
        >
          {{ item.label }}
        </a>
        <div class="pt-4 space-y-3 border-t border-slate-800 mt-4">
          <template v-if="!isAuthenticated">
            <UButton
              @click="showLoginModal = true"
              variant="ghost"
              color="neutral"
              class="w-full justify-start gap-2"
            >
              <LogIn class="h-4 w-4" />
              Вход в кабинет
            </UButton>
          </template>
          <template v-else>
            <UButton
              @click="goToCabinet"
              variant="ghost"
              color="neutral"
              class="w-full justify-start gap-2"
            >
              Кабинет
            </UButton>
            <UButton
              v-if="isImpersonated"
              @click="onStopImpersonate"
              variant="ghost"
              color="neutral"
              class="w-full justify-start gap-2"
            >
              Выйти из имперсонации
            </UButton>
            <UButton
              @click="onLogout"
              variant="ghost"
              color="neutral"
              class="w-full justify-start gap-2"
            >
              Выйти
            </UButton>
          </template>
          <a
            href="https://t.me/Maksim_Belichenko"
            target="_blank"
            rel="noopener noreferrer"
            class="block w-full"
          >
            <Button
              class="w-full justify-center bg-gradient-to-r from-primary-600 to-accent-600 text-white hover:from-primary-500 hover:to-accent-500 font-bold shadow-lg"
            >
              Связаться в Telegram
            </Button>
          </a>
        </div>
      </div>
    </div>
  </nav>
  <UModal v-model:open="showLoginModal" title="Логин">
    <template #body>
      <div class="tab-panel">
        <div id="telegram-login-container" class="flex justify-center my-4"></div>
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { useAuth } from '@/composables/use-auth'
import type { UserLoginIn } from '@/types/openapi'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Menu, X, Send, LogIn } from 'lucide-vue-next'
import Button from './Button.vue'
import type { NavItem } from './types'

const navItems: NavItem[] = [
  { label: 'Возможности', href: '#features' },
  { label: 'Результаты', href: '#testimonials' },
  { label: 'Команда', href: '#team' },
  { label: 'Тарифы', href: '#pricing' },
  { label: 'FAQ', href: '#faq' },
]

const isOpen = ref(false)
const scrolled = ref(false)

const navBackground = computed(() =>
  scrolled.value || isOpen.value
    ? 'bg-slate-900/80 backdrop-blur-md border-b border-slate-800'
    : 'bg-transparent',
)

const handleScroll = () => {
  scrolled.value = window.scrollY > 20
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
})

const router = useRouter()
const { login, logout, stopImpersonate, isAuthenticated, isImpersonated } = useAuth()
const showLoginModal = ref(false)

const TELEGRAM_BOT_USERNAME = import.meta.env.BOT_NAME
const USE_MOCK_LOGIN = TELEGRAM_BOT_USERNAME == 'MockBot'

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
    "first_name": "mock",
    "last_name": "mock",
    "username": "mock",
    "photo_url": "mock",
    "auth_date": 0,
    "hash": "mock"
}`

function parseUserLogin(raw: string): UserLoginIn {
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
  handleScroll()
  window.addEventListener('scroll', handleScroll)
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

const goToCabinet = async () => {
  isOpen.value = false
  await router.push({ name: 'app' })
}

const onLogout = async () => {
  isOpen.value = false
  await logout()
}

const onStopImpersonate = async () => {
  isOpen.value = false
  await stopImpersonate()
  await router.push('/app/admin')
}

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
