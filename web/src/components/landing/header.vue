<template>
  <UHeader>
    <template #left>
      <RouterLink to="/">
        <Logo />
      </RouterLink>
    </template>
    <template #right>
      <UButton
        @click="handleLogin"
        icon="i-lucide-log-in"
        variant="subtle"
        class="hidden lg:block"
      />
      <UColorModeButton />
    </template>
    <template #body>
      <UButton
        @click="handleLogin"
        class="mt-4"
        icon="i-lucide-log-in"
        label="Войти"
        variant="subtle"
        block
      />
    </template>
  </UHeader>
</template>
<script setup lang="ts">
import Logo from '@/components/shared/logo.vue'
import { useAuth } from '@/composables/use-auth'
import type { UserLoginIn } from '@/types/openapi'

const { login } = useAuth()

const mockTelegramUser: UserLoginIn = {
  id: 359107176,
  firstName: 'М',
  lastName: 'С',
  username: 'chernyakoff',
  photoUrl: 'https://t.me/i/userpic/320/E5CF1DXAc92hvxFoNm0Z4y4Z4ycjpk6DqbKdvmjyVyw.jpg',
  authDate: 1760377923,
  hash: '464897237d5917afb80676e35d45fb75f90c348e120fa649dd57a97af7f69c5b',
}

const handleLogin = () => {
  login(mockTelegramUser).then(() => {})
}
</script>
