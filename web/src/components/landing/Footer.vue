<script setup lang="ts">
import { ref } from 'vue';
import { Send } from 'lucide-vue-next';
import Modal from './Modal.vue';

const isOfferOpen = ref(false);
const isPrivacyOpen = ref(false);
</script>

<template>
  <footer class="bg-slate-950/80 backdrop-blur-md text-slate-400 py-12 border-t border-slate-900/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
        <div class="col-span-1 md:col-span-1">
          <div class="flex items-center gap-2 mb-4 text-white">
            <Send class="h-6 w-6 text-primary-500" />
            <span class="font-bold text-xl uppercase">Лидоруб</span>
          </div>
          <p class="text-sm text-slate-500 mb-6">
            Профессиональный инструмент для лидогенерации. Забудьте о рутине, сосредоточьтесь на продажах.
          </p>
        </div>

        <div>
          <h4 class="text-white font-semibold mb-4">Сервис</h4>
          <ul class="space-y-2 text-sm">
            <li><a href="#features" class="hover:text-primary-400 transition-colors">Возможности</a></li>
            <li><a href="#pricing" class="hover:text-primary-400 transition-colors">Тарифы</a></li>
            <li><a href="#testimonials" class="hover:text-primary-400 transition-colors">Кейсы</a></li>
          </ul>
        </div>

        <div>
          <h4 class="text-white font-semibold mb-4">Компания</h4>
          <ul class="space-y-2 text-sm">
            <li><a href="#team" class="hover:text-primary-400 transition-colors">Команда</a></li>
          </ul>
        </div>

        <div>
          <h4 class="text-white font-semibold mb-4">Легальность</h4>
          <ul class="space-y-2 text-sm">
            <li>
              <button class="hover:text-primary-400 transition-colors text-left" @click="isPrivacyOpen = true">
                Политика конфиденциальности
              </button>
            </li>
            <li>
              <button class="hover:text-primary-400 transition-colors text-left" @click="isOfferOpen = true">
                Оферта
              </button>
            </li>
          </ul>
        </div>
      </div>

      <div class="pt-8 border-t border-slate-900/50 text-center text-sm text-slate-600">
        © 2022 Quasar Technologies. Все права защищены.
      </div>
    </div>

    <Modal :isOpen="isPrivacyOpen" title="Политика конфиденциальности" @close="isPrivacyOpen = false">
      <p class="mb-4">
        Мы не собираем, не храним и не передаем третьим лицам ваши персональные данные, за исключением случаев,
        необходимых для технического функционирования сервиса.
      </p>
      <p>
        Наш сервис является инструментом автоматизации (SaaS) и не осуществляет обработку данных пользователей за
        пределами функционала, предоставляемого по лицензии.
      </p>
    </Modal>

    <Modal :isOpen="isOfferOpen" title="Публичная оферта" @close="isOfferOpen = false">
      <p class="mb-4">
        Настоящий документ является публичной офертой на использование программного обеспечения «Лидоруб» (далее —
        Сервис).
      </p>
      <p class="mb-4">
        1. Предмет оферты: Лицензиар предоставляет Пользователю право использования Сервиса на условиях простой
        (неисключительной) лицензии.
      </p>
      <p class="mb-4">
        2. Пользователь обязуется использовать Сервис в соответствии с законодательством и правилами платформы Telegram.
      </p>
      <p>3. Сервис предоставляется по принципу «как есть».</p>
    </Modal>
  </footer>
</template>
