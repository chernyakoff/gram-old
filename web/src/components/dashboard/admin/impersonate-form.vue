<!-- AdminImpersonate.vue -->
<template>
    <UForm ref="form" :schema="impersonateSchema" :state="state" @submit="onSubmit">
        <UFormField label="Username" name="username" class="mb-4">
            <UInput
                v-model="state.username"
                size="md"
                class="w-full"
                :disabled="loading || stopLoading"
                icon="i-lucide-at-sign" />
        </UFormField>
        <div class="flex flex-wrap gap-3">
            <UButton type="submit" :loading="loading" :disabled="loading || stopLoading">
                Войти как пользователь
            </UButton>
            <UButton
                v-if="isImpersonated"
                type="button"
                color="neutral"
                variant="outline"
                icon="i-lucide-user-round-x"
                :loading="stopLoading"
                :disabled="loading || stopLoading"
                @click="onStopImpersonate">
                Выйти из имперсонации
            </UButton>
        </div>

        <!-- Успешный результат -->
        <div v-if="impersonateSuccess" class="mt-6">
            <UAlert
                color="success"
                variant="soft"
                title="Успешно"
                description="Вход выполнен. Перенаправление..."
                icon="i-heroicons-check-circle" />
        </div>
        <div v-if="stopSuccess" class="mt-6">
            <UAlert
                color="success"
                variant="soft"
                title="Успешно"
                description="Имперсонация отключена."
                icon="i-heroicons-check-circle" />
        </div>
        <!-- Ошибка -->
        <div v-if="impersonateError" class="mt-6">
            <UAlert
                color="error"
                variant="solid"
                title="Ошибка"
                :description="impersonateError"
                icon="i-heroicons-exclamation-triangle" />
        </div>
        <div v-if="stopError" class="mt-6">
            <UAlert
                color="error"
                variant="solid"
                title="Ошибка"
                :description="stopError"
                icon="i-heroicons-exclamation-triangle" />
        </div>
    </UForm>
</template>
<script setup lang="ts">
import { impersonateSchema, type ImpersonateSchema } from '@/schemas/admin'
import type { ImpersonateIn } from '@/types/openapi'
import type { FormSubmitEvent } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useAuth } from '@/composables/use-auth'

const title = 'Админка - Имперсонация'

useTitle(title)

const { impersonate, stopImpersonate, isImpersonated, user } = useAuth()

const state = reactive({
    username: '',
})

const loading = ref(false)
const stopLoading = ref(false)
const impersonateSuccess = ref(false)
const impersonateError = ref<string | null>(null)
const stopSuccess = ref(false)
const stopError = ref<string | null>(null)

let successTimer: number | null = null
let stopSuccessTimer: number | null = null

async function getApiErrorMessage(e: unknown): Promise<string | null> {
    const err = e as { response?: Response; message?: unknown } | null
    const response: Response | undefined = err?.response
    if (response) {
        try {
            const data = await response.clone().json()
            if (typeof data?.detail === 'string') return data.detail
        } catch {
            // ignore
        }
    }

    if (err?.message && typeof err.message === 'string') return err.message
    return null
}

function scheduleHide(refFlag: { value: boolean }, ms = 2500) {
    if (successTimer) {
        clearTimeout(successTimer)
        successTimer = null
    }
    successTimer = window.setTimeout(() => {
        refFlag.value = false
    }, ms)
}

function scheduleHideStop(refFlag: { value: boolean }, ms = 2500) {
    if (stopSuccessTimer) {
        clearTimeout(stopSuccessTimer)
        stopSuccessTimer = null
    }
    stopSuccessTimer = window.setTimeout(() => {
        refFlag.value = false
    }, ms)
}

onBeforeUnmount(() => {
    if (successTimer) clearTimeout(successTimer)
    if (stopSuccessTimer) clearTimeout(stopSuccessTimer)
})

watch(() => state.username, (newValue) => {
    if (newValue.startsWith('@')) {
        state.username = newValue.slice(1)
    }
})

const onStopImpersonate = async () => {
    stopSuccess.value = false
    stopError.value = null
    stopLoading.value = true

    try {
        await stopImpersonate()
        stopSuccess.value = true
        scheduleHideStop(stopSuccess, 2500)
    } catch (e) {
        stopError.value = 'Не удалось выйти из имперсонации'
        console.error('Stop impersonate error:', e)
    } finally {
        stopLoading.value = false
    }
}

const onSubmit = async (event: FormSubmitEvent<ImpersonateSchema>) => {
    impersonateSuccess.value = false
    impersonateError.value = null
    stopSuccess.value = false
    stopError.value = null
    loading.value = true

    try {
        const data = event.data satisfies ImpersonateIn

        const normalized = data.username.trim().replace(/^@/, '')
        // Convenience: if admin is currently impersonating and tries to "login" as the current user again,
        // interpret it as a request to exit impersonation.
        if (isImpersonated.value && normalized && normalized === (user.value?.username ?? '')) {
            await onStopImpersonate()
            return
        }
        if (!isImpersonated.value && normalized && normalized === (user.value?.username ?? '')) {
            // Self-impersonation is confusing; to "switch to yourself" use stop impersonation (when active).
            impersonateError.value = 'Нельзя имперсонировать самого себя'
            return
        }

        await impersonate(data)

        impersonateSuccess.value = true
        scheduleHide(impersonateSuccess, 2500)
        // Редирект произойдёт автоматически через watch в useAuth
    } catch (e) {
        const msg = await getApiErrorMessage(e)
        // Map known backend errors to RU strings.
        if (msg === 'Cannot impersonate yourself') {
            impersonateError.value = 'Нельзя имперсонировать самого себя'
        } else if (msg === 'User not found') {
            impersonateError.value = 'Пользователь не найден'
        } else {
            impersonateError.value = msg || 'Ошибка'
        }
        console.error('Impersonate error:', e)
    } finally {
        loading.value = false
    }
}
</script>
