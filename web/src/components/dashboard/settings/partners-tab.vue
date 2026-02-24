<template>
  <div class="space-y-8">
    <!-- Реферальная ссылка -->
    <div class="space-y-2">
      <h2 class="text-xl font-semibold mb-4">Ваша реферальная ссылка</h2>
      <div
        @click="copyLink"
        class="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors flex items-center justify-between group">
        <code class="text-sm break-all">{{ refLink }}</code>
        <UIcon
          :name="copied ? 'i-heroicons-check' : 'i-heroicons-clipboard-document'"
          class="w-5 h-5 flex-shrink-0 ml-4 group-hover:text-primary-500 transition-colors" />
      </div>
      <p v-if="copied" class="text-sm text-green-600 dark:text-green-400"> Ссылка скопирована в буфер обмена </p>
    </div>
    <!-- Ваш пригласитель -->
    <div v-if="partners?.referredBy" class="space-y-4">
      <h2 class="text-xl font-semibold">Ваш пригласитель</h2>
      <UPageList>
        <UPageCard
          variant="ghost"
          :to="partners.referredBy.username ? `https://t.me/${partners.referredBy.username}` : undefined"
          :target="partners.referredBy.username ? '_blank' : undefined">
          <template #body>
            <UUser
              :name="getUserName(partners.referredBy)"
              :description="partners.referredBy.username ? `@${partners.referredBy.username}` : `ID: ${partners.referredBy.id}`"
              :avatar="{
                src: partners.referredBy.photoUrl || undefined,
                alt: getUserName(partners.referredBy)
              }"
              size="xl"
              class="relative"
              :ui="{
                name: 'truncate',
                description: 'truncate'
              }" />
          </template>
        </UPageCard>
      </UPageList>
    </div>
    <!-- Приглашенные вами -->
    <div v-if="partners?.referrals" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">Приглашенные вами</h2>
        <span class="text-sm text-gray-600 dark:text-gray-400"> Количество: {{ partners.referrals.length }}
        </span>
      </div>
      <div v-if="partners.referrals.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400"> У вас пока нет приглашенных пользователей </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UPageCard v-for="(referral, index) in partners.referrals" :key="index" variant="ghost" :to="referral.username ? `https://t.me/${referral.username}` : undefined" :target="referral.username ? '_blank' : undefined">
          <template #body>
            <UUser
              :name="getUserName(referral)"
              :description="referral.username ? `@${referral.username}` : `ID: ${referral.id}`"
              :avatar="{
                src: referral.photoUrl || undefined,
                alt: getUserName(referral)
              }"
              size="xl"
              class="relative"
              :ui="{
                name: 'truncate',
                description: 'truncate'
              }" />
          </template>
        </UPageCard>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useAuth } from '@/composables/use-auth';
import { usePartners } from '@/composables/use-partners';
import type { PartnerOut } from '@/types/openapi';
import { useTitle } from '@vueuse/core'
import { useClipboard } from '@vueuse/core'
import { computed, onMounted, ref } from 'vue';

const title = 'Настройки - Партнерка'
useTitle(title)

const { user } = useAuth()
const toast = useToast()
const { copy, isSupported } = useClipboard()

const copied = ref(false)
const refLink = computed(() => `${import.meta.env.WEB_URL}/r/${user.value?.refCode ?? ''}`)

const { getPartners } = usePartners()

const partners = ref<PartnerOut>()

// Вспомогательная функция для получения имени пользователя
const getUserName = (user: { firstName?: string | null, lastName?: string | null, username?: string | null, id: number }) => {
  let name = ''
  if (user.firstName || user.lastName) {
    name = [user.firstName, user.lastName].filter(Boolean).join(' ')
  } else if (user.username) {
    name = user.username
  } else {
    name = `Пользователь ${user.id}`
  }

  // Обрезаем до 30 символов
  return name.length > 30 ? name.substring(0, 30) + '...' : name
}

const copyLink = async () => {
  if (!isSupported.value) {
    toast.add({
      title: "Clipboard API не поддерживается этим браузером",
      color: 'red',
    })
    return
  }

  await copy(refLink.value)
  copied.value = true


  // Убираем подсказку через 2 секунды
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

onMounted(async () => {
  partners.value = await getPartners()
})
</script>
