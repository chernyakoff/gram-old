<template>
  <UDashboardPanel id="calendar">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="w-full max-w-4xl mx-auto md:min-w-[800px] px-4">
        <UTabs :items="tabs" variant="link" :ui="{ trigger: 'grow' }" class="gap-4">
          <template #meetings><CalendarMeetings /></template>
          <template #settings><CalendarSettings /></template>
        </UTabs>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import { useTitle } from '@vueuse/core'
import CalendarSettings from '@/components/dashboard/calendar/settings-tab.vue'
import CalendarMeetings from '@/components/dashboard/calendar/meetings-tab.vue'
const title = 'Календарь'

const tabs = [
  { label: 'Встречи', icon: 'bx:bxs-calendar-check', slot: 'meetings' as const },
  { label: 'Настройки', icon: 'bx:cog', slot: 'settings' as const },
] satisfies TabsItem[]
/*
хочу сделать редктируемый список рабочих интервалов
vue + nuxt ui (только компоненты)


в столбик выстроить строчки для каждого дня недели
в каждой строчке
1) кружок с буквой начала дня (П, В, С, Ч, П, С, В)
2) поле ввода интервала - можно редатировать руками, но можно выбрать из списка c шагом 15 минут (00:00, 00:15,...)
3) тире
4) поле ввода интервала - можно редатировать руками, но можно выбрать из списка c шагом 15 минут (00:00, 00:15,...)
5) кнопка удалить (крестик) - если ее нажать, то в строчке остается только кружок из п.1 а рядом надпись Выкл. и за ней кнопка с иконкой плюс, которая включает строчку назад
6) кнопка с иконкой плюс, которая позволяет добавить строчку под текущую, в которой будет только два поля для ввода интевалов и кнопка удалить (крестик), что позволяет задать на один день несколько интервалов
7) кнопка копировать, при нажатии на которую рядом с кнопкой появлется попап где галочками можно отметить дни недели куда будут скопированы интерваоы с этой строки и под ней (если есть)

надо чтоб все сохранялось на сервере при любых изменениях

*/
useTitle(title)
</script>
