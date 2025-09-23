<template>
  <UForm :schema="schema" :state="modelValue">
    <UFormField label="Username" name="username" class="mb-4">
      <UInput v-model="state.username" size="md" class="w-full" icon="i-lucide-at-sign" />
    </UFormField>

    <div class="flex gap-4 mb-4">
      <UFormField label="Имя" name="firstName" class="flex-1">
        <UInput v-model="state.firstName" size="md" class="w-full" />
      </UFormField>
      <UFormField label="Фамилия" name="lastName" class="flex-1">
        <UInput v-model="state.lastName" size="md" class="w-full" />
      </UFormField>
    </div>

    <UFormField label="О себе" name="about" class="mb-4">
      <UTextarea v-model="state.about" class="w-full" :rows="3" />
    </UFormField>

    <UFormField label="Канал" name="channel">
      <UInput v-model="state.channel" size="md" class="w-full" icon="i-lucide-at-sign" />
    </UFormField>
  </UForm>
</template>

<script setup lang="ts">
import { useVModel } from '@vueuse/core'
import { accountSchema, type AccountSchema } from '@/schemas/account'

const props = defineProps<{
  modelValue: AccountSchema
  schema: typeof accountSchema
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: AccountSchema): void
}>()

// proxy вокруг modelValue, который можно менять безопасно
const state = useVModel(props, 'modelValue', emit)
</script>
