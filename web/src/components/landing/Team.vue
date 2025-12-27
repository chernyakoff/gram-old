<script setup lang="ts">
import type { TeamMember } from './types'

const team: TeamMember[] = [
  {
    name: 'Макс Беличенко',
    role: 'Основатель Quasar Technologies',
    imageUrl: '/Max.jpg',
    bio: '',
  },
  {
    name: 'Давид Фонтана',
    role: 'Основатель (главный маркетолог)',
    imageUrl: '/David.jpg',
    bio: '',
  },
  {
    name: 'Слава Миллер',
    role: 'Стратегический консультант по ИИ-продуктам',
    imageUrl: '/Slava.jpg',
    bio: '',
  },
  {
    name: 'Михаил Черняков',
    role: 'Ведущий разработчик Quasar',
    imageUrl: '/Misha.jpg',
    bio: '',
  },
]
</script>

<template>
  <section id="team" class="py-20 bg-transparent relative">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl">Команда экспертов</h2>
        <p class="mt-4 text-lg text-slate-400">
          Мы практики, которые каждый день работают с трафиком в Telegram.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        <div
          v-for="(member, index) in team"
          :key="index"
          class="bg-slate-900/50 backdrop-blur-md rounded-2xl overflow-hidden shadow-lg hover:shadow-primary-900/20 transition-all duration-300 flex flex-col items-center text-center p-6 border border-slate-700 hover:border-slate-600 group"
        >
          <div class="relative w-32 h-32 mb-6">
            <div
              class="absolute inset-0 bg-gradient-to-br from-primary-500 to-accent-600 rounded-full blur opacity-20 group-hover:opacity-40 transition-opacity"
            ></div>
            <img
              class="w-full h-full object-cover rounded-full ring-2 ring-slate-600 relative z-10"
              :src="member.imageUrl"
              :alt="member.name"
            />
          </div>
          <h3 class="text-xl font-bold text-white">{{ member.name }}</h3>
          <p class="text-primary-400 font-medium text-sm mb-4">{{ member.role }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
