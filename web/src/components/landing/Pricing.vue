<script setup lang="ts">
import { Check } from 'lucide-vue-next'
import Button from './Button.vue'
import type { PricingPlan } from './types'

const plans: PricingPlan[] = [
  {
    name: 'Базовый',
    price: '24 900 ₽ / год',
    period: '',
    description: 'Полный доступ ко всему функционалу платформы для самостоятельной работы.',
    features: [
      'До 20 аккаунтов',
      '1 проект',
      'Полный доступ к ИИ инструментам',
      'Автоупаковка и Внутренняя CRM',
      'Поддержка в общем чате комьюнити',
    ],
    buttonText: 'Получить доступ',
  },
  {
    name: 'Стандарт',
    price: '44 900 ₽ / год',
    period: '',
    description: 'Для тех, кому нужна помощь в стратегии и быстрых результатах.',
    features: [
      'До 60 аккаунтов',
      'До 3 проектов',
      'Приоритетная техническая поддержка',
      'Помощь в составлении офферов',
      'Аудит ваших кампаний',
    ],
    isPopular: true,
    buttonText: 'Получить доступ',
  },
  {
    name: 'Безлимит',
    price: '74 900 ₽',
    period: '',
    description: 'Мы берем настройку кампаний на себя. Идеально для крупных клиентов.',
    features: [
      'Неограниченно аккаунтов',
      'Неограниченно проектов',
      'Помощь в сборе кампаний под ключ',
      'Индивидуальные консультации',
      'Стратегическое планирование',
    ],
    buttonText: 'Обсудить условия',
  },
]
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
    </div>
  </section>
</template>
