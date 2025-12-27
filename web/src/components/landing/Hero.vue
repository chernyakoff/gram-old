<script setup lang="ts">
import { ArrowRight, PlayCircle, Bot, Zap, Cpu } from 'lucide-vue-next';
import Button from './Button.vue';
</script>

<template>
  <div class="relative pt-32 pb-16 lg:pt-48 lg:pb-28 overflow-hidden bg-transparent">
    <div class="absolute top-0 left-0 w-full h-full z-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-[10%] -right-[5%] w-[500px] h-[500px] bg-primary-600/10 rounded-full blur-[100px] animate-pulse"></div>
      <div class="absolute -bottom-[10%] -left-[10%] w-[600px] h-[600px] bg-accent-600/10 rounded-full blur-[120px]"></div>
      <div class="absolute top-[40%] left-1/2 -translate-x-1/2 w-[800px] h-[300px] bg-blue-500/5 rounded-full blur-[100px] rotate-12"></div>
    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
      <div class="max-w-4xl mx-auto">
        <div
          class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-800/50 border border-slate-700 backdrop-blur-sm text-primary-300 text-xs font-semibold mb-8 uppercase tracking-wider shadow-lg shadow-primary-900/20"
        >
          <span class="flex h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
          SaaS Платформа для роста
        </div>

        <h1
          class="text-4xl md:text-6xl lg:text-7xl font-extrabold text-white tracking-tight mb-8 leading-tight drop-shadow-lg font-montserrat"
        >
          Ваша личная армия <br class="hidden md:block" />
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 via-blue-400 to-accent-500">
            ИИ-менеджеров
          </span>
        </h1>

        <p
          class="text-lg md:text-xl text-slate-300 mb-12 leading-relaxed max-w-2xl mx-auto drop-shadow-md"
        >
          Получите доступ к платформе, где сотни виртуальных сотрудников работают 24/7 без зарплаты.
          ИИ сам упакует аккаунты, найдет клиентов и доведет диалог до заявки.
        </p>

        <div class="flex flex-col sm:flex-row gap-5 justify-center items-center mb-16">
          <a
            href="https://t.me/Maksim_Belichenko"
            target="_blank"
            rel="noopener noreferrer"
            class="w-full sm:w-auto"
          >
            <Button
              size="lg"
              class="w-full sm:w-auto gap-2 bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-500 hover:to-accent-500 border-none shadow-lg shadow-primary-900/50"
            >
              Получить доступ <ArrowRight class="h-5 w-5" />
            </Button>
          </a>

          <a
            href="https://www.youtube.com/watch?v=oaSkBLolVA4"
            target="_blank"
            rel="noopener noreferrer"
            class="w-full sm:w-auto"
          >
            <Button
              variant="outline"
              size="lg"
              class="w-full sm:w-auto gap-2 border-slate-700 text-slate-300 hover:bg-slate-800/50 hover:text-white backdrop-blur-sm"
            >
              <PlayCircle class="h-5 w-5" /> Демонстрация
            </Button>
          </a>
        </div>

        <div class="flex flex-wrap justify-center gap-x-8 gap-y-4 text-sm text-slate-400">
          <div class="flex items-center gap-2">
            <Bot class="h-4 w-4 text-primary-400" />
            <span>Передовые модели</span>
          </div>
          <div class="flex items-center gap-2">
            <Cpu class="h-4 w-4 text-primary-400" />
            <span>Авто-упаковка профилей</span>
          </div>
          <div class="flex items-center gap-2">
            <Zap class="h-4 w-4 text-primary-400" />
            <span>Быстрый старт</span>
          </div>
        </div>
      </div>

      <div class="mt-20 relative mx-auto max-w-3xl group">
        <div
          class="relative rounded-2xl bg-slate-900/50 backdrop-blur-md p-2 ring-1 ring-inset ring-slate-700/50 lg:-m-4 lg:rounded-3xl lg:p-4 shadow-2xl shadow-primary-900/50"
        >
          <div
            class="bg-slate-900/50 rounded-xl overflow-hidden border border-slate-800 relative aspect-video flex items-center justify-center"
          >
            <div
              class="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1639322537228-f710d846310a?q=80&w=2232&auto=format&fit=crop')] bg-cover bg-center opacity-30 mix-blend-overlay"
            ></div>
            <div class="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/50 to-transparent"></div>

            <div class="relative z-10 w-full h-full flex items-center justify-center p-8">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl">
                <div
                  class="bg-slate-800/80 backdrop-blur-md border border-slate-700 p-4 rounded-xl flex flex-col gap-2 transform translate-y-4"
                >
                  <div class="h-2 w-20 bg-primary-500/50 rounded animate-pulse"></div>
                  <div
                    class="h-10 w-full bg-slate-700/50 rounded flex items-center px-3 text-xs text-slate-400 font-mono"
                  >
                    > Generative Bios... OK
                  </div>
                </div>
                <div
                  class="bg-slate-800/80 backdrop-blur-md border border-primary-500/30 p-4 rounded-xl flex flex-col gap-2 transform -translate-y-4 shadow-lg shadow-primary-500/10"
                >
                  <div class="h-2 w-24 bg-accent-500/50 rounded animate-pulse"></div>
                  <div
                    class="h-10 w-full bg-slate-700/50 rounded flex items-center px-3 text-xs text-green-400 font-mono"
                  >
                    > 15 New Leads Found
                  </div>
                </div>
                <div
                  class="bg-slate-800/80 backdrop-blur-md border border-slate-700 p-4 rounded-xl flex flex-col gap-2 transform translate-y-4"
                >
                  <div class="h-2 w-16 bg-blue-500/50 rounded animate-pulse"></div>
                  <div
                    class="h-10 w-full bg-slate-700/50 rounded flex items-center px-3 text-xs text-slate-400 font-mono"
                  >
                    > Anti-Spam Check... 100%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div
          class="absolute -inset-1 bg-gradient-to-r from-primary-600 to-accent-600 rounded-3xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200 -z-10"
        ></div>
      </div>
    </div>
  </div>
</template>
