<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <div class="flex items-center space-x-2">
    <img src="@/assets/logo.svg" alt="Neurogram" class="h-8" />
    <span v-if="!collapsed" class="font-bold text-lg">Neurogram</span>
  </div>
</template>
<script setup lang="ts">

defineProps<{
  collapsed?: boolean
}>()
</script>
