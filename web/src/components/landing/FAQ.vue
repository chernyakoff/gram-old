<script setup lang="ts">
import { Plus, Minus } from 'lucide-vue-next'
import { ref } from 'vue'
import type { FAQItem } from './types'

const faqItems: FAQItem[] = [
  {
    question: 'Вы настраиваете все за меня?',
    answer:
      'Мы — SaaS сервис. Мы предоставляем вам мощный инструмент (софт), доступ к ИИ и инфраструктуру. Настройка происходит вами через простой интерфейс, где ИИ делает 90% работы (пишет тексты, упаковывает аккаунты).',
  },
  {
    question: 'Нужно ли мне покупать аккаунты отдельно?',
    answer:
      'Нет, искать поставщиков не нужно. Вы можете купить аккаунты, прокси и Telegram Premium прямо внутри нашего сервиса. Ценообразование полностью прозрачно: аккаунты часто дешевле рыночных, а токены — строго по рынку.',
  },
  {
    question: 'Сложно ли разобраться в интерфейсе?',
    answer:
      'Нет, интерфейс создан для предпринимателей, а не программистов. Чтобы запустить рассылку, вам нужно просто ответить на вопросы о вашем бизнесе, остальное сделает авто-упаковщик и ИИ.',
  },
  {
    question: 'Насколько это безопасно?',
    answer:
      'Правила платформы меняются, и мы постоянно адаптируемся. Мы используем выделенные прокси и систему, имитирующую поведение человека, чтобы работа сервиса соответствовала текущим условиям Telegram и минимизировала риски.',
  },
]

const openIndex = ref<number | null>(0)

const toggle = (index: number) => {
  openIndex.value = openIndex.value === index ? null : index
}
</script>

<template>
  <section id="faq" class="py-20 bg-slate-900/30 backdrop-blur-sm border-t border-slate-800/50">
    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Вопросы о платформе
        </h2>
      </div>

      <div class="space-y-4">
        <div
          v-for="(item, index) in faqItems"
          :key="index"
          class="bg-slate-800/40 backdrop-blur-md rounded-xl border border-slate-700 overflow-hidden hover:border-slate-600 transition-colors"
        >
          <button
            class="w-full px-6 py-4 flex items-center justify-between text-left focus:outline-none"
            @click="toggle(index)"
          >
            <span class="text-lg font-medium text-slate-200 pr-8">{{ item.question }}</span>
            <Minus v-if="openIndex === index" class="h-5 w-5 text-primary-400 flex-shrink-0" />
            <Plus v-else class="h-5 w-5 text-slate-500 flex-shrink-0" />
          </button>
          <div
            class="transition-all duration-300 ease-in-out overflow-hidden"
            :class="openIndex === index ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'"
          >
            <div class="px-6 pb-6 text-slate-400 leading-relaxed border-t border-slate-700/50 pt-4">
              {{ item.answer }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
