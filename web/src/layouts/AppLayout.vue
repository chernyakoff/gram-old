<template>
  <Suspense>
    <UApp>
      <UDashboardGroup unit="rem" storage="local">
        <AppSidebar />
        <RouterView />
      </UDashboardGroup>
    </UApp>
  </Suspense>
</template>
<script setup lang="ts">

import { useStorage } from '@vueuse/core'
import AppSidebar from './components/AppSidebar.vue'
const toast = useToast()


const cookie = useStorage('cookie-consent', 'pending')
if (cookie.value !== 'accepted') {
  toast.add({
    title: 'We use first-party cookies to enhance your experience on our website.',
    duration: 0,
    close: false,
    actions: [{
      label: 'Accept',
      color: 'neutral',
      variant: 'outline',
      onClick: () => {
        cookie.value = 'accepted'
      }
    }, {
      label: 'Opt out',
      color: 'neutral',
      variant: 'ghost'
    }]
  })
}
</script>
