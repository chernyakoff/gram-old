<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <h1>Добро пожаловать, @{{ user?.username }}</h1>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import { useAuth } from '@/composables/useAuth'
import { useTitle } from '@vueuse/core'
const { user } = useAuth()
const title = "Главная"
useTitle(title)

</script>
