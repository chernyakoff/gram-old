<template>
  <UApp :toaster="{ expand: false }">
    <Header />
    <UMain>
      <RouterView />
    </UMain>
  </UApp>
</template>
<script setup lang="ts">
import Header from '@/components/landing/header.vue'
</script>
