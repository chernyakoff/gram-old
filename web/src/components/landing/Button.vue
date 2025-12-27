<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
  }>(),
  {
    variant: 'primary',
    size: 'md',
  }
);

const baseStyles =
  'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';

const variants: Record<string, string> = {
  primary:
    'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500 shadow-md hover:shadow-lg',
  secondary:
    'bg-slate-900 text-white hover:bg-slate-800 focus:ring-slate-900 shadow-sm',
  outline:
    'border border-slate-300 bg-transparent text-slate-700 hover:bg-slate-50 focus:ring-primary-500',
  ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 hover:text-slate-900',
};

const sizes: Record<string, string> = {
  sm: 'h-9 px-4 text-sm',
  md: 'h-11 px-6 text-base',
  lg: 'h-14 px-8 text-lg',
};
</script>

<template>
  <button v-bind="$attrs" :class="[baseStyles, variants[props.variant], sizes[props.size]]">
    <slot />
  </button>
</template>
