<template>
  <UForm :schema="accountSchema" :state="editor.profile">
    <UFormField
      label="Username"
      name="username"
      class="mb-4"
      :error="props.validationErrors.username"
    >
      <UInput
        v-model="editor.profile.username"
        size="md"
        class="w-full"
        icon="i-lucide-at-sign"
        @blur="validateField('username')"
      />
    </UFormField>

    <div class="flex gap-4 mb-4">
      <UFormField
        label="Имя"
        name="firstName"
        class="flex-1"
        :error="props.validationErrors.firstName"
      >
        <UInput
          v-model="editor.profile.firstName"
          size="md"
          class="w-full"
          @blur="validateField('firstName')"
        />
      </UFormField>
      <UFormField
        label="Фамилия"
        name="lastName"
        class="flex-1"
        :error="props.validationErrors.lastName"
      >
        <UInput
          v-model="editor.profile.lastName"
          size="md"
          class="w-full"
          @blur="validateField('lastName')"
        />
      </UFormField>
    </div>

    <UFormField
      label="О себе"
      name="about"
      class="mb-4"
      :error="props.validationErrors.about"
      :hint="aboutHint"
    >
      <UTextarea
        v-model="editor.profile.about"
        class="w-full"
        :rows="3"
        @blur="validateField('about')"
      />
    </UFormField>

    <UFormField label="Канал" name="channel" :error="props.validationErrors.channel">
      <UInput
        v-model="editor.profile.channel"
        size="md"
        class="w-full"
        icon="i-lucide-at-sign"
        @blur="validateField('channel')"
      />
    </UFormField>
  </UForm>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import * as v from 'valibot'
import { useAccountEditor } from '@/stores/account-store'
import { accountSchema } from '@/schemas/accounts'

const props = defineProps<{
  validationErrors: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'update:validationErrors', errors: Record<string, string>): void
}>()

const editor = useAccountEditor()

const aboutHint = computed(() => {
  const maxLength = editor.profile.premium ? 140 : 70
  const currentLength = editor.profile.about?.length || 0
  return `${currentLength}/${maxLength} символов`
})

async function validateField(fieldName: keyof typeof editor.profile) {
  try {
    await v.parseAsync(accountSchema, editor.profile)
    // Очищаем ошибку для этого поля
    if (props.validationErrors[fieldName]) {
      const newErrors = { ...props.validationErrors }
      delete newErrors[fieldName]
      emit('update:validationErrors', newErrors)
    }
  } catch (err) {
    if (err instanceof v.ValiError) {
      // Проверяем, есть ли ошибка для текущего поля
      const fieldError = err.issues.find((issue) => issue.path?.[0]?.key === fieldName)
      if (fieldError) {
        emit('update:validationErrors', {
          ...props.validationErrors,
          [fieldName]: fieldError.message,
        })
      }
    }
  }
}
</script>
