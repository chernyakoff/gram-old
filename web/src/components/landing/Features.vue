<script setup lang="ts">
import { Bot, Shield, BarChart3, Users, RefreshCw, PenTool } from 'lucide-vue-next'
import type { Feature } from './types'

const features: Feature[] = [
  {
    title: 'Автоупаковка Аккаунтов',
    description:
      'Система сама генерирует имена, био и ставит реалистичные фото. Профили выглядят как живые люди, что повышает доверие.',
    icon: RefreshCw,
  },
  {
    title: 'Промт-инжиниринг без кода',
    description:
      'Вам не нужно писать скрипты. Ответьте на вопросы о продукте, и ИИ сам создаст идеальную стратегию общения.',
    icon: PenTool,
  },
  {
    title: 'Экологичный подход',
    description:
      'ИИ не спамит "в лоб". Сначала знакомство, потом выявление интереса, и только затем — нативный оффер.',
    icon: Bot,
  },
  {
    title: 'Встроенная CRM',
    description:
      'Наблюдайте за диалогами в реальном времени. Статистика, статусы "менеджеров" и управление подписками в одном окне.',
    icon: BarChart3,
  },
  {
    title: 'Минимизация рисков',
    description:
      'Система минимизирует риски блокировки за счет рандомизации сообщений и имитации человеческого поведения.',
    icon: Shield,
  },
  {
    title: 'Масштаб в клик',
    description:
      '1 аккаунт стартует 10 диалогов в сутки. Нужно больше? Подключите 50-100 аккаунтов прямо в интерфейсе.',
    icon: Users,
  },
]
</script>

<template>
  <section id="features" class="py-20 bg-transparent relative">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-base font-semibold text-primary-400 uppercase tracking-widest">
          Инструментарий
        </h2>
        <p class="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Ваши преимущества
        </p>
        <p class="mt-4 text-lg text-slate-400">
          Мы предоставляем SaaS-платформу, где сложные процессы выполняются искусственным
          интеллектом за считанные минуты.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12">
        <div
          v-for="(feature, index) in features"
          :key="index"
          class="relative group p-8 rounded-2xl bg-slate-900/40 border border-slate-700/50 hover:border-primary-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-primary-900/20 backdrop-blur-md"
        >
          <div
            class="absolute top-8 left-8 bg-slate-900 p-3 rounded-xl border border-slate-700 group-hover:border-primary-500 group-hover:text-primary-400 transition-colors duration-300 shadow-lg"
          >
            <component
              :is="feature.icon"
              class="h-6 w-6 text-slate-300 group-hover:text-primary-400 transition-colors"
            />
          </div>
          <div class="mt-16">
            <h3
              class="text-xl font-bold text-white mb-3 group-hover:text-primary-400 transition-colors"
            >
              {{ feature.title }}
            </h3>
            <p class="text-slate-400 leading-relaxed text-sm">
              {{ feature.description }}
            </p>
          </div>
          <div
            class="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary-600/5 to-accent-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
          ></div>
        </div>
      </div>
    </div>
  </section>
</template>
