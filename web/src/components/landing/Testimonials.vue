<script setup lang="ts">
import { Star, MessageCircle } from 'lucide-vue-next';
import type { Testimonial } from '../types';

const testimonials: Testimonial[] = [
  {
    content:
      'Никогда не думал, что Telegram может давать столько лидов. За первый месяц получили 45 квалифицированных заявок на консалтинг.',
    author: 'Дмитрий В.',
    role: 'Основатель',
    company: 'CryptoConsult',
    avatarUrl: 'https://picsum.photos/seed/dima/100/100',
  },
  {
    content:
      'Работаем как агентство, отдали парсинг и рассылку ребятам на аутсорс. Клиенты довольны, мы разгрузили свой саппорт. Отличный white-label.',
    author: 'Алина К.',
    role: 'Маркетолог',
    company: 'Digital Agency X',
    avatarUrl: 'https://picsum.photos/seed/alina/100/100',
  },
  {
    content:
      'Боялись банов, но технология действительно безопасная. Конверсия в ответ выше, чем в email рассылках в 10 раз.',
    author: 'Сергей П.',
    role: 'Head of Sales',
    company: 'EdTech Start',
    avatarUrl: 'https://picsum.photos/seed/sergey/100/100',
  },
];
</script>

<template>
  <section
    id="testimonials"
    class="py-20 bg-slate-900/40 backdrop-blur-sm text-white overflow-hidden relative border-t border-slate-800/50"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-bold tracking-tight sm:text-4xl">Результаты наших клиентов</h2>
        <p class="mt-4 text-slate-400">Реальные кейсы использования холодных рассылок</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div
          v-for="(item, index) in testimonials"
          :key="index"
          class="bg-slate-900/60 backdrop-blur-md p-8 rounded-2xl border border-slate-700/50 hover:border-primary-500/30 transition-all duration-300 hover:-translate-y-1 shadow-lg"
        >
          <div class="flex justify-between items-start mb-6">
            <div class="flex gap-1">
              <Star v-for="star in 5" :key="star" class="h-4 w-4 text-yellow-500 fill-yellow-500" />
            </div>
            <MessageCircle class="h-6 w-6 text-slate-700 opacity-50" />
          </div>

          <blockquote class="text-lg text-slate-300 mb-6 leading-relaxed">
            "{{ item.content }}"
          </blockquote>
          <div class="flex items-center gap-4 border-t border-slate-800/50 pt-6">
            <img
              :src="item.avatarUrl"
              :alt="item.author"
              class="h-10 w-10 rounded-full object-cover ring-2 ring-primary-900"
            />
            <div>
              <div class="font-semibold text-white text-sm">{{ item.author }}</div>
              <div class="text-xs text-slate-500">{{ item.role }}, {{ item.company }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
