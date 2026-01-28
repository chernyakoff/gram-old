<script setup lang="ts">
import { ref } from 'vue'
import { Check } from 'lucide-vue-next'
import Button from './Button.vue'
import Modal from './Modal.vue'
import type { PricingPlan } from './types'
import { useForms } from '@/composables/use-forms'

const { sendCallback } = useForms()

const plans: PricingPlan[] = [
  {
    name: 'ВСЁ САМ',
    price: '34 900 ₽',
    period: '',
    description: 'Включает в себя',
    features: ['1 год', '1 проект', 'До 20 аккаунтов'],
    buttonText: 'Получить доступ',
  },
  {
    name: 'СОПРОВОЖДЕНИЕ',
    price: '59 900 ₽',
    period: '',
    description: 'Включает в себя',
    features: ['1 год', 'до 3 проектов', 'До 60 аккаунтов', 'Доступ к сервису ECHO в подарок'],
    isPopular: true,
    buttonText: 'Получить доступ',
  },
  {
    name: 'ПОД КЛЮЧ',
    price: '89 900 ₽',
    period: '',
    description: 'Включает в себя',
    features: ['ПОЛНАЯ УПАКОВКА', 'БЕЗЛИМИТНЫЙ ТАРИФ'],
    buttonText: 'Обсудить условия',
  },
]

const showCallbackModal = ref(false)
const showConsentText = ref(false)
const isSubmitting = ref(false)
const submissionStatus = ref<'idle' | 'success' | 'error'>('idle')
const errorMessage = ref('')
const consentText = ref('')
const form = ref({
  name: '',
  phone: '',
  telegram: '',
  consent: false,
})

const resetForm = () => {
  form.value = { name: '', phone: '', telegram: '', consent: false }
}

const openCallbackModal = () => {
  submissionStatus.value = 'idle'
  errorMessage.value = ''
  showCallbackModal.value = true
}

const closeCallbackModal = () => {
  showCallbackModal.value = false
  showConsentText.value = false
  resetForm()
}

const handleSubmit = async () => {
  errorMessage.value = ''

  if (!form.value.name.trim() || !form.value.phone.trim() || !form.value.consent) {
    errorMessage.value =
      'Пожалуйста, заполните имя, телефон и отметьте согласие на обработку данных.'
    return
  }

  isSubmitting.value = true
  submissionStatus.value = 'idle'

  try {
    await sendCallback({
      name: form.value.name.trim(),
      phone: form.value.phone.trim(),
      telegram: form.value.telegram.trim(),
    })
    submissionStatus.value = 'success'
    resetForm()
  } catch (error) {
    submissionStatus.value = 'error'
    errorMessage.value =
      error instanceof Error ? error.message : 'Не удалось отправить заявку. Попробуйте позже.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section id="pricing" class="py-20 bg-transparent relative overflow-hidden">
    <div
      class="absolute top-1/2 left-1/4 w-96 h-96 bg-primary-900/20 rounded-full blur-[100px] pointer-events-none"
    ></div>
    <div
      class="absolute bottom-0 right-1/4 w-96 h-96 bg-accent-900/20 rounded-full blur-[100px] pointer-events-none"
    ></div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Тарифы на доступ к платформе
        </h2>
        <p class="mt-4 text-lg text-slate-400">
          Вы платите ТОЛЬКО за лицензию на использование софта. Расходные материалы (оплата токенов
          дополнительно) и аккаунты приобретаются внутри сервиса.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div
          v-for="(plan, index) in plans"
          :key="index"
          :class="[
            'relative flex flex-col p-8 rounded-2xl border transition-all duration-300 backdrop-blur-md',
            plan.isPopular
              ? 'bg-slate-800/80 border-primary-500 shadow-2xl shadow-primary-900/20 md:-translate-y-4'
              : 'bg-slate-900/50 border-slate-700 hover:border-slate-600',
          ]"
        >
          <div
            v-if="plan.isPopular"
            class="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-primary-600 to-accent-600 text-white px-4 py-1 rounded-full text-sm font-bold uppercase tracking-wide shadow-lg"
          >
            Рекомендуем
          </div>

          <div class="mb-6">
            <h3 class="text-lg font-semibold text-white">{{ plan.name }}</h3>
            <div class="mt-4 flex items-baseline text-white">
              <span class="text-2xl font-bold text-slate-400 tracking-tight">
                {{ plan.price }}
              </span>
              <span v-if="plan.period" class="ml-1 text-xl font-semibold text-slate-500">
                {{ plan.period }}
              </span>
            </div>
            <p class="mt-4 text-sm text-slate-400">{{ plan.description }}</p>
          </div>

          <ul class="space-y-4 mb-8 flex-1">
            <li v-for="(feature, fIndex) in plan.features" :key="fIndex" class="flex items-start">
              <Check
                class="h-5 w-5 flex-shrink-0 mr-3"
                :class="plan.isPopular ? 'text-primary-400' : 'text-slate-500'"
              />
              <span class="text-sm text-slate-300">{{ feature }}</span>
            </li>
          </ul>

          <a
            href="https://t.me/Maksim_Belichenko"
            target="_blank"
            rel="noopener noreferrer"
            class="block"
          >
            <Button
              :variant="plan.isPopular ? 'primary' : 'outline'"
              :class="[
                'w-full transition-all duration-300',
                plan.isPopular
                  ? 'bg-gradient-to-r from-primary-600 to-accent-600 border-none shadow-lg shadow-primary-900/40 hover:shadow-primary-500/40 hover:from-primary-500 hover:to-accent-500'
                  : 'border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800/50 hover:border-primary-500/50 hover:shadow-lg hover:shadow-primary-900/20',
              ]"
            >
              {{ plan.buttonText }}
            </Button>
          </a>
        </div>
      </div>

      <div
        class="mt-16 relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-r from-primary-900/60 via-slate-900 to-accent-900/50 p-8 md:p-12 shadow-2xl shadow-primary-900/20"
      >
        <div class="absolute inset-y-0 right-0 w-64 md:w-80 opacity-40 pointer-events-none">
          <div
            class="w-full h-full bg-gradient-radial from-primary-500/30 via-transparent to-transparent blur-3xl"
          ></div>
        </div>
        <div class="relative z-10 flex flex-col md:flex-row items-center gap-8">
          <div class="flex-1">
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">
              Запросить звонок
            </p>
            <h3 class="mt-2 text-2xl md:text-3xl font-bold text-white">
              Хотите обсудить тариф или задать вопрос?
            </h3>
            <p class="mt-3 text-base text-slate-300 max-w-2xl">
              Оставьте контакты — менеджер перезвонит в рабочее время и поможет подобрать
              оптимальный формат работы.
            </p>
          </div>
          <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
            <Button
              variant="primary"
              class="w-full sm:w-auto bg-gradient-to-r from-primary-600 to-accent-600 border-none shadow-lg shadow-primary-900/40 hover:from-primary-500 hover:to-accent-500"
              @click="openCallbackModal"
            >
              Запросить звонок
            </Button>
            <div class="text-xs text-slate-400">
              <div class="flex items-center gap-2">
                <span class="inline-flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Ответ в течение рабочего дня</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Modal :is-open="showCallbackModal" title="Оставьте контакты" @close="closeCallbackModal">
      <form class="space-y-6" @submit.prevent="handleSubmit">
        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-200">Имя</label>
            <input
              v-model="form.name"
              type="text"
              name="name"
              autocomplete="name"
              class="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-50 placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 transition-colors"
              placeholder="Как к вам обращаться?"
              required
            />
          </div>
          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-200">Телефон</label>
            <input
              v-model="form.phone"
              type="tel"
              name="phone"
              autocomplete="tel"
              class="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-50 placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 transition-colors"
              placeholder="+7 (___) ___-__-__"
              required
            />
          </div>
          <div class="space-y-2 md:col-span-2">
            <label class="block text-sm font-medium text-slate-200">Ник в Telegram</label>
            <div
              class="flex items-center rounded-xl border border-slate-700 bg-slate-900/60 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500 transition-colors"
            >
              <span class="px-4 text-slate-500">@</span>
              <input
                v-model="form.telegram"
                type="text"
                name="telegram"
                class="w-full bg-transparent px-1 py-3 pr-4 text-slate-50 placeholder-slate-500 focus:outline-none"
                placeholder="username (необязательно)"
              />
            </div>
          </div>
        </div>

        <div class="space-y-3">
          <label class="flex items-start gap-3 cursor-pointer">
            <input
              v-model="form.consent"
              type="checkbox"
              class="mt-1 h-5 w-5 rounded border-slate-600 bg-slate-900 text-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-0"
              required
            />
            <span class="text-sm text-slate-300 leading-tight">
              Даю согласие на обработку персональных данных для связи по моей заявке.
              <button
                type="button"
                class="ml-2 text-xs text-primary-300 hover:text-primary-200 underline underline-offset-4"
                @click="showConsentText = !showConsentText"
              >
                Показать текст согласия
              </button>
            </span>
          </label>
          <div
            v-if="showConsentText"
            class="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-xs text-slate-400 min-h-[72px] whitespace-pre-line"
          >
            {{ consentText || ' ' }}
          </div>
        </div>

        <div
          v-if="submissionStatus === 'success'"
          class="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100"
        >
          Заявка отправлена! Мы свяжемся с вами в ближайшее время.
        </div>

        <div
          v-if="submissionStatus === 'error' || errorMessage"
          class="rounded-xl border border-rose-500/50 bg-rose-500/10 px-4 py-3 text-sm text-rose-100"
        >
          {{ errorMessage || 'Не удалось отправить заявку. Попробуйте еще раз.' }}
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <Button
            type="submit"
            variant="primary"
            :disabled="isSubmitting"
            class="w-full sm:w-auto bg-gradient-to-r from-primary-600 to-accent-600 border-none shadow-lg shadow-primary-900/40 hover:from-primary-500 hover:to-accent-500"
          >
            {{ isSubmitting ? 'Отправляем...' : 'Отправить заявку' }}
          </Button>
          <button
            type="button"
            class="text-sm text-slate-400 hover:text-white transition-colors"
            @click="closeCallbackModal"
          >
            Отмена
          </button>
        </div>
      </form>
    </Modal>
  </section>
</template>
