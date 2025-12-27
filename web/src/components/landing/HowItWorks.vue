<script setup lang="ts">
import { UserPlus, Settings, Rocket, MessageSquare } from 'lucide-vue-next'
import type { Step } from './types'

const steps: Step[] = [
  {
    number: '01',
    title: 'Регистрация в SaaS',
    description:
      'Вы получаете доступ к личному кабинету. Подключение аккаунтов (прокси, премиум) происходит внутри платформы в пару кликов.',
    icon: UserPlus,
  },
  {
    number: '02',
    title: 'Настройка ИИ',
    description:
      'Просто ответьте на вопросы о вашем продукте и ЦА. ИИ сам сгенерирует промпты и стратегии диалогов.',
    icon: Settings,
  },
  {
    number: '03',
    title: 'Запуск Армии',
    description:
      'Активируйте 10, 50 или 100 ИИ-менеджеров. Система сама упакует профили и начнет диалоги с клиентами после запуска.',
    icon: Rocket,
  },
  {
    number: '04',
    title: 'Получение Лидов',
    description:
      'ИИ ведет диалоги по выбранной базе, отрабатывает возражения и передает вам только готовые заявки.',
    icon: MessageSquare,
  },
]
</script>

<template>
  <section class="py-20 bg-slate-900/30 backdrop-blur-sm relative border-t border-slate-800/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          От старта до первых лидов — 30 минут
        </h2>
        <p class="mt-4 text-slate-400">
          Вам не нужно быть программистом. Интерфейс интуитивно понятен.
        </p>
      </div>

      <div class="relative">
        <div
          class="hidden lg:block absolute top-1/2 left-0 w-full h-0.5 bg-slate-800 -translate-y-1/2 z-0"
        ></div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div
            v-for="(step, index) in steps"
            :key="index"
            class="relative z-10 bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-slate-700/50 hover:border-primary-500/50 transition-all duration-300"
          >
            <div
              class="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mb-6 border border-slate-700 mx-auto lg:mx-0"
            >
              <component :is="step.icon" class="h-6 w-6 text-primary-400" />
            </div>
            <div
              class="text-4xl font-bold text-slate-800 absolute top-4 right-4 opacity-50 select-none"
            >
              {{ step.number }}
            </div>
            <h3 class="text-xl font-bold text-white mb-3 text-center lg:text-left">
              {{ step.title }}
            </h3>
            <p class="text-slate-400 text-sm leading-relaxed text-center lg:text-left">
              {{ step.description }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
