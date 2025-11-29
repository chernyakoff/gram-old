<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <div class="flex items-center space-x-2">
    <img
      src="@/assets/logo.svg"
      alt="Lidorub"
      class="h-8 invert-0 dark:invert brightness-0 dark:brightness-100"
    />

    <span v-if="!collapsed" class="font-bold text-lg">Lidorub</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  collapsed?: boolean
}>()
</script>
