<template>
  <UApp :toaster="{ expand: false }">
    <MainHeader />
    <UMain>
      <RouterView />
    </UMain>
  </UApp>
</template>
<script setup lang="ts">
import MainHeader from '@/layouts/components/MainHeader.vue'
</script>
