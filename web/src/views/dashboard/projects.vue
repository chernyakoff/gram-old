<template>
  <UDashboardPanel id="projects">
    <template #header>
      <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <CreateProjectModal @close="refresh" />
        </template>
      </UDashboardNavbar>
    </template>
    <template #body>
      <div class="min-w-[600px] max-w-4xl mx-auto">
        <UTable
          ref="table"
          v-model:column-filters="columnFilters"
          v-model:column-visibility="columnVisibility"
          class="shrink-0 w-full"
          :data="projects"
          :columns="columns"
          :loading="loading"
          :ui="{
            base: 'table-fixed border-separate border-spacing-0',
            thead: '[&>tr]:bg-elevated/50 [&>tr]:after:content-none',
            tbody: '[&>tr]:last:[&>td]:border-b-0',
            th: 'py-2 first:rounded-l-lg last:rounded-r-lg border-y border-default first:border-l last:border-r',
            td: 'border-b border-default',
          }"
        >
          <template #status-cell="{ row }">
            <UBadge
              class="opacity-50"
              :label="row.original.status ? 'АКТИВЕН' : 'ВЫКЛЮЧЕН'"
              :color="row.original.status ? 'secondary' : 'warning'"
            />
          </template>
          <template #actions-cell="{ row }">
            <div class="flex items-center gap-2 w-42">
              <USwitch
                title="Изменить статус"
                :modelValue="row.original.status"
                @update:modelValue="(val: boolean) => toggleStatus(row.original, val)"
              />
              <ChatModal :id="row.original.id" />
              <UButton
                title="Редактировать проект"
                variant="ghost"
                icon="lucide:edit"
                :to="{ name: 'project', params: { id: row.original.id } }"
              />

              <DeleteModal :id="row.original.id" @close="refresh" />
            </div>
          </template>
        </UTable>
      </div>
    </template>
  </UDashboardPanel>
</template>
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { ref, onMounted } from 'vue'
import { useTitle } from '@vueuse/core'
import DeleteModal from '@/components/dashboard/projects/delete-modal.vue'
import ChatModal from '@/components/dashboard/projects/chat-modal.vue'
import CreateProjectModal from '@/components/dashboard/projects/create-modal.vue'
//import FilesDrawer from '@/components/dashboard/projects/files-drawer.vue'
import { useProjects } from '@/composables/use-projects'

import type { ProjectShortOut } from '@/types/openapi'

const { projects, get, loading, status } = useProjects()

const title = 'Проекты'
useTitle(title)

onMounted(() => get())

const toast = useToast()

// - drawer

//- table
const columnFilters = ref([{ id: 'name', value: '' }])
const columnVisibility = ref()

const refresh = () => {
  get()
}
const toggleStatus = async (project: ProjectShortOut, value: boolean) => {
  const prev = project.status

  // временно показываем переключение
  project.status = value

  const res = await status(project.id, value)

  if (res.result !== 'success') {
    // откат
    project.status = prev

    toast.add({
      title: 'Нельзя активировать проект',
      description: res.errors.join('\n'),
      color: 'error',
      ui: { description: 'whitespace-pre-line' },
    })
  }
}

const columns: TableColumn<ProjectShortOut>[] = [
  {
    accessorKey: 'name',
    header: 'Название',
  },

  {
    accessorKey: 'status',
    header: 'Статус',
  },
  {
    accessorKey: 'actions',
    header: 'Действия',
    /* meta: {
      class: {
        th: 'w-42',
      },
    }, */
  },
]
</script>
