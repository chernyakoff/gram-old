<script setup lang="ts">
import { Teleport, onBeforeUnmount, watch } from 'vue';
import { X } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
  title: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const handleEscape = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    emit('close');
  }
};

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEscape);
    } else {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleEscape);
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  document.body.style.overflow = '';
  window.removeEventListener('keydown', handleEscape);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="props.isOpen"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm"
    >
      <div
        class="relative w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]"
      >
        <div class="flex items-center justify-between p-6 border-b border-slate-800">
          <h3 class="text-xl font-bold text-white">{{ props.title }}</h3>
          <button @click="emit('close')" class="text-slate-400 hover:text-white transition-colors">
            <X class="h-6 w-6" />
          </button>
        </div>
        <div class="p-6 overflow-y-auto text-slate-300 leading-relaxed">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>
