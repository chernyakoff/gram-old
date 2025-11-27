<template>
  <UModal
    v-model:open="open"
    title="Изменение страны"
    :description="`Будет изменено ${selectedIds.length} прокси.`"
  >
    <UButton
      v-if="selectedIds.length"
      label="Изменить страну"
      color="neutral"
      variant="subtle"
      icon="bx:world"
    >
      <template #trailing>
        <UKbd>
          {{ selectedIds.length }}
        </UKbd>
      </template>
    </UButton>
    <template #body>
      <UFormField name="projectId" label="Укажите страну" :error="error">
        <USelectMenu
          v-model="country"
          :items="countries"
          class="w-full"
          :search-input="{
            placeholder: 'Поиск...',
            icon: 'bx:search',
          }"
        />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton label="Отмена" color="neutral" variant="subtle" @click="open = false" />
        <UButton label="Изменить" color="primary" variant="solid" loading-auto @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
<script setup lang="ts">
import { ref } from 'vue'

import type { ProxiesCountryIn } from '@/types/openapi'
import { useProxies } from '@/composables/use-proxies'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const country = ref('')

const { selectedIds } = defineProps<{
  selectedIds: number[]
}>()

const open = defineModel<boolean>('open', { default: false })
const error = ref<string | undefined>(undefined)

// prettier-ignore
const countries = [
  "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT",
  "AZ","BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW",
  "BV","BR","IO","BN","BG","BF","BI","KH","CM","CA","CV","KY","CF","TD","CL",
  "CN","CX","CC","CO","KM","CG","CD","CK","CR","CI","HR","CU","CW","CY","CZ",
  "DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ",
  "FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL","GD","GP",
  "GU","GT","GG","GN","GW","GY","HT","HM","VA","HN","HK","HU","IS","IN","ID",
  "IR","IQ","IE","IM","IL","IT","JM","JP","JE","JO","KZ","KE","KI","KP","KR",
  "KW","KG","LA","LV","LB","LS","LR","LY","LI","LT","LU","MO","MG","MW","MY",
  "MV","ML","MT","MH","MQ","MR","MU","YT","MX","FM","MD","MC","MN","ME","MS",
  "MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI","NE","NG","NU","NF","MK",
  "MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH","PN","PL","PT","PR",
  "QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","PM","VC","WS","SM","ST",
  "SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS","SS","ES",
  "LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK","TO",
  "TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","UM","US","UY","UZ","VU",
  "VE","VN","VG","VI","WF","EH","YE","ZM","ZW"
];

const { changeCountry } = useProxies()

async function onSubmit() {
  if (!country.value) {
    error.value = 'Пожалуйста, выберите страну'
    return
  }

  error.value = undefined

  const data: ProxiesCountryIn = {
    country: country.value,
    ids: selectedIds,
  }

  await changeCountry(data)
  open.value = false
  emit('close')
}
</script>
