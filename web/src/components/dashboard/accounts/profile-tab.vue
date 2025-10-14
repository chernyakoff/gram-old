<template>
  <UForm :schema="accountSchema" :state="editor.profile">
    <UFormField label="Username" name="username" class="mb-4">
      <UInput v-model="editor.profile.username" size="md" class="w-full" icon="i-lucide-at-sign" />
    </UFormField>

    <div class="flex gap-4 mb-4">
      <UFormField label="Имя" name="firstName" class="flex-1">
        <UInput v-model="editor.profile.firstName" size="md" class="w-full" />
      </UFormField>
      <UFormField label="Фамилия" name="lastName" class="flex-1">
        <UInput v-model="editor.profile.lastName" size="md" class="w-full" />
      </UFormField>
    </div>

    <UFormField label="О себе" name="about" class="mb-4">
      <UTextarea v-model="editor.profile.about" class="w-full" :rows="3" />
    </UFormField>

    <UFormField label="Канал" name="channel">
      <UInput v-model="editor.profile.channel" size="md" class="w-full" icon="i-lucide-at-sign" />
    </UFormField>
  </UForm>
</template>

<script setup lang="ts">
import { useAccountEditor } from '@/stores/account-store'
import { accountSchema } from '@/schemas/accounts'
const editor = useAccountEditor()
</script>
