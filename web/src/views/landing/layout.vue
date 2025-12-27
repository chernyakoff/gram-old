<template>
  <div class="landing min-h-screen text-slate-50 relative">
    <!--  <NeuralNoise :opacity="0.5" :timeScale="0.5" /> -->
    <div class="relative z-10">
      <LandindNavbar />
      <main>
        <RouterView />
      </main>
      <LandindFooter />
    </div>
  </div>
</template>
<script setup lang="ts">
import '@/assets/landing.css'
import LandindNavbar from '@/components/landing/Navbar.vue'
import LandindFooter from '@/components/landing/Footer.vue'
//import NeuralNoise from '@/components/landing/NeuralNoise.vue'
</script>
