<template>
  <div class="card">
    <Panel header="Лицензия не найдена">
      <p>Пожалуйста, приобретите доступ</p>
      <button @click="buyLicense">Купить лицензию</button>
    </Panel>
  </div>
</template>
<script setup lang="ts">
function buyLicense () {
  alert('Здесь логика покупки лицензии')
}
</script>
