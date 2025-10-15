import { h, computed, useTemplateRef } from 'vue'
import type { Table } from '@tanstack/vue-table'
import type { TableColumn } from '@nuxt/ui'

import Checkbox from '@nuxt/ui/components/Checkbox.vue'
export function useTableSelection<TableRow extends object>(
  tableRefName: string,
  pkName: keyof TableRow = 'id' as keyof TableRow,
) {
  const tableRef = useTemplateRef<{ tableApi: Table<TableRow> }>(tableRefName)
  const tableApi = computed(() => tableRef.value?.tableApi || null)

  const selectedIds = computed<number[]>(() => {
    if (!tableApi.value) return []

    return tableApi.value.getSelectedRowModel().rows.map((row) => {
      const orig = row.original as { [key in keyof TableRow]: unknown }

      if (!(pkName in orig)) {
        throw new Error(`Row does not have the primary key field '${String(pkName)}'`)
      }

      const value = orig[pkName]
      if (typeof value !== 'number') {
        throw new Error(`Primary key field '${String(pkName)}' is not a number`)
      }

      return value
    })
  })

  function selectionColumn(): TableColumn<TableRow> {
    return {
      id: 'select',
      header: ({ table }) =>
        h(Checkbox, {
          modelValue: table.getIsSomePageRowsSelected()
            ? 'indeterminate'
            : table.getIsAllPageRowsSelected(),
          'onUpdate:modelValue': (value: boolean | 'indeterminate') =>
            table.toggleAllPageRowsSelected(!!value),
          ariaLabel: 'Выбрать всё',
        }),
      cell: ({ row }) =>
        h(Checkbox, {
          modelValue: row.getIsSelected(),
          'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
          ariaLabel: 'Выбрать проекты',
        }),
    }
  }

  return {
    tableApi,
    selectedIds,
    selectionColumn,
  }
}
