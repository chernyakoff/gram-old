<template>
  <router-view />
</template>
<script setup lang="ts">
import { useSSE } from '@/composables/useSSE'

const { connect } = useSSE()
connect()
</script>
