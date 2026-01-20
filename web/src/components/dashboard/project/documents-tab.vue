<template>
  <div class="w-full max-w-4xl mx-auto md:min-w-[800px] px-4">
    <UTable
      ref="table"
      class="shrink-0 w-full mb-4 mt-4"
      :data="documents"
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
      <template #actions-cell="{ row }">
        <div class="flex items-center gap-2">
          <UButton
            :to="(row.original as ProjectDocumentOut).url"
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
            @click="openDeleteModal(row.original as ProjectDocumentOut)"
          />
        </div>
      </template>
    </UTable>

    <div class="flex justify-end mt-4">
      <UploadDocumentsModal :project-id="projectId" @completed="refresh" />
    </div>
  </div>
  <ConfirmModal
    v-model="isConfirmModalOpen"
    title="Подтверждение удаления"
    :description="`Вы уверены, что хотите удалить '${selectedItem?.filename}'?`"
    @confirm="handleDelete"
  />
</template>
<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import UploadDocumentsModal from '@/components/dashboard/project/documents-modal.vue'
import ConfirmModal from '@/components/shared/confirm-modal.vue'

import { onMounted, ref } from 'vue'
import type { ProjectDocumentOut } from '@/types/openapi'
import { useProjects } from '@/composables/use-projects'
import { formatBytes } from '@/utils/filesize'
import { mimeAliases } from '@/utils/mime'

const { projectId } = defineProps<{
  projectId: number
}>()

const { getDocuments, loading, deleteDocument } = useProjects()

const isConfirmModalOpen = ref(false)

const selectedItem = ref<ProjectDocumentOut>()

const documents = ref<ProjectDocumentOut[]>([])

const refresh = async () => {
  const response = await getDocuments(projectId)
  documents.value = response
}

function openDeleteModal(item: ProjectDocumentOut) {
  selectedItem.value = item
  isConfirmModalOpen.value = true
}

async function handleDelete() {
  if (selectedItem.value) {
    await deleteDocument(projectId, selectedItem.value.id)
    await refresh()
  }
}

onMounted(async () => {
  await refresh()
})

const columns: TableColumn<ProjectDocumentOut>[] = [
  {
    accessorKey: 'filename',
    header: 'Файл',
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
