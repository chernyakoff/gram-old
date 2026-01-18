<template>
  <div class="w-full max-w-4xl mx-auto md:min-w-[800px] px-4">
    <UTable
      ref="table"
      class="shrink-0 w-full mb-4 mt-4"
      :data="files"
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
      <template #title-cell="{ row }">
        <UPopover mode="hover">
          <p class="truncate w-32">
            {{ row.getValue('title') }}
          </p>
          <template #content>
            {{ row.getValue('title') }}
          </template>
        </UPopover>
      </template>
      <template #actions-cell="{ row }">
        <div class="flex items-center gap-2">
          <UButton
            title="Редактировать"
            variant="ghost"
            icon="lucide:edit"
            @click="openEditModal(row.original as ProjectFileOut)"
          />

          <UButton
            :to="(row.original as ProjectFileOut).url"
            title="Скачать"
            variant="ghost"
            icon="lucide:download"
            download
            target="_blank"
            external
          />

          <UButton
            title="Удалить"
            variant="ghost"
            icon="lucide:trash"
            @click="openDeleteModal(row.original as ProjectFileOut)"
          />
        </div>
      </template>
    </UTable>

    <div class="flex justify-end mt-4">
      <UploadFilesModal :project-id="projectId" @completed="refresh" />
    </div>
  </div>
  <ConfirmModal
    v-model="isConfirmModalOpen"
    title="Подтверждение удаления"
    :description="`Вы уверены, что хотите удалить '${selectedItem?.filename}'?`"
    @confirm="handleDelete"
  />
  <ProjectFileEditModal
    v-if="selectedItem"
    :key="selectedItem.id"
    v-model="isEditModalOpen"
    :file="selectedItem"
    :project-id="projectId"
    @close="refresh"
  />
</template>
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import UploadFilesModal from '@/components/dashboard/project/files-modal.vue'
import ConfirmModal from '@/components/shared/confirm-modal.vue'
import ProjectFileEditModal from '@/components/dashboard/project/file-edit-modal.vue'
import { nextTick, onMounted, ref } from 'vue'
import type { ProjectFileOut } from '@/types/openapi'
import { useProjects } from '@/composables/use-projects'
import { formatBytes } from '@/utils/filesize'
import { mimeAliases } from '@/utils/mime'

const { projectId } = defineProps<{
  projectId: number
}>()

const { getFiles, loading, deleteFile } = useProjects()

const isConfirmModalOpen = ref(false)
const isEditModalOpen = ref(false)

const selectedItem = ref<ProjectFileOut>()

const files = ref<ProjectFileOut[]>([])

const refresh = async () => {
  const response = await getFiles(projectId)
  files.value = response
}

function openDeleteModal(item: ProjectFileOut) {
  selectedItem.value = item
  isConfirmModalOpen.value = true
}

function openEditModal(item: ProjectFileOut) {
  selectedItem.value = undefined // сброс
  // следом через nextTick
  nextTick(() => {
    selectedItem.value = item
    isEditModalOpen.value = true
  })
}

async function handleDelete() {
  if (selectedItem.value) {
    await deleteFile(projectId, selectedItem.value.id)
    const response = await getFiles(projectId)
    files.value = response
  }
}

onMounted(async () => {
  const response = await getFiles(projectId)
  files.value = response
})

const columns: TableColumn<ProjectFileOut>[] = [
  {
    accessorKey: 'filename',
    header: 'Файл',
  },
  {
    accessorKey: 'status',
    header: 'Статус',
  },
  {
    accessorKey: 'title',
    header: 'Описание',
  },
  {
    accessorKey: 'contentType',
    header: 'Тип',
    cell: ({ row }) => {
      const contentType = row.getValue('contentType') as string
      return mimeAliases[contentType] || contentType
    },
  },
  {
    accessorKey: 'fileSize',
    header: 'Размер',
    cell: ({ row }) => {
      return formatBytes(row.getValue('fileSize'))
    },
  },
  {
    accessorKey: 'actions',
    header: ' ',
  },
]
</script>
