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
import Logo from '@/components/shared/Logo.vue'
import { useAuth } from '@/composables/useAuth'

const { login } = useAuth()

const mockTelegramUser: TelegramUser = {
  id: 359107176,
  firstName: 'М',
  lastName: 'С',
  username: 'chernyakoff',
  photoUrl: 'https://t.me/i/userpic/320/E5CF1DXAc92hvxFoNm0Z4y4Z4ycjpk6DqbKdvmjyVyw.jpg',
  authDate: 1758471696,
  hash: '9389c9e21ece6c4d5d468d9b2bacb895a341c9900f420934cc5dc51125c763fb',
}

const handleLogin = () => {
  login(mockTelegramUser).then(() => {})
}
</script>
