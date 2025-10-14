<template>
  <router-view />
</template>
<script setup lang="ts">
import { useSSE } from '@/composables/use-sse'

const { connect } = useSSE()
connect()
</script>
