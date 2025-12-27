<script setup lang="ts">
import { XCircle, CheckCircle } from 'lucide-vue-next'
import type { ComparisonPoint } from './types'

const comparisons: ComparisonPoint[] = [
  {
    feature: 'Первый контакт',
    oldWay: 'Длинное полотно текста с ссылкой в лоб',
    newWay: 'Короткое приветствие, вопрос по теме, имитация живого интереса',
  },
  {
    feature: 'Реакция на отказ',
    oldWay: 'Игнор или повторный спам',
    newWay: 'Отработка возражения, попытка выяснить причину',
  },
  {
    feature: 'Безопасность',
    oldWay: 'Массовые баны аккаунтов каждый день',
    newWay: 'Минимальный риск благодаря рандомизации и паузам',
  },
  {
    feature: 'Настройка',
    oldWay: 'Нужен софт, сервер, прокси, навыки кода',
    newWay: 'Все внутри облачного сервиса, настройка мышкой',
  },
]
</script>

<template>
  <section class="py-20 bg-transparent relative">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Почему спам умер, а ИИ работает
        </h2>
        <p class="mt-4 text-slate-400">
          Сравните старые методы рассылок и нашу технологию умных диалогов.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
        <div class="bg-red-900/10 border border-red-900/30 rounded-2xl p-8 backdrop-blur-sm">
          <h3 class="text-2xl font-bold text-red-400 mb-8 flex items-center gap-2">
            <XCircle class="h-6 w-6" />
            Обычный спам
          </h3>
          <div class="space-y-6">
            <div
              v-for="(item, index) in comparisons"
              :key="index"
              class="border-b border-red-900/20 pb-4 last:border-0 last:pb-0"
            >
              <div class="text-xs text-red-300/50 uppercase mb-1">{{ item.feature }}</div>
              <div class="text-slate-300">{{ item.oldWay }}</div>
            </div>
          </div>
        </div>

        <div
          class="bg-green-900/10 border border-green-900/30 rounded-2xl p-8 relative overflow-hidden backdrop-blur-sm"
        >
          <div
            class="absolute top-0 right-0 w-32 h-32 bg-green-500/10 blur-[50px] rounded-full"
          ></div>
          <h3 class="text-2xl font-bold text-green-400 mb-8 flex items-center gap-2">
            <CheckCircle class="h-6 w-6" />
            ИИ Диалоги (SaaS)
          </h3>
          <div class="space-y-6">
            <div
              v-for="(item, index) in comparisons"
              :key="index"
              class="border-b border-green-900/20 pb-4 last:border-0 last:pb-0"
            >
              <div class="text-xs text-green-300/50 uppercase mb-1">{{ item.feature }}</div>
              <div class="text-white font-medium">{{ item.newWay }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
