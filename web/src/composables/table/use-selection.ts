import { h, computed, useTemplateRef } from 'vue'
import type { VNodeChild } from 'vue'
import type { Table } from '@tanstack/vue-table'
import type { TableColumn } from '@nuxt/ui'
import Checkbox from '@nuxt/ui/components/Checkbox.vue'

export function useTableSelection<TableRow extends object>(
  tableRefName: string,
  pkName: keyof TableRow = 'id' as keyof TableRow,
  options?: {
    isSelectable?: (row: TableRow) => boolean
    renderNonSelectable?: (row: TableRow) => VNodeChild
  },
) {
  const tableRef = useTemplateRef<{ tableApi: Table<TableRow> }>(tableRefName)
  const tableApi = computed(() => tableRef.value?.tableApi || null)

  const selectedIds = computed<number[]>(() => {
    if (!tableApi.value) return []

    return tableApi.value.getSelectedRowModel().rows.map((row) => {
      const orig = row.original as TableRow

      if (!(pkName in orig)) {
        throw new Error(`Row does not have the primary key field '${String(pkName)}'`)
      }

      const value = orig[pkName] as unknown
      if (typeof value !== 'number') {
        throw new Error(`Primary key field '${String(pkName)}' is not a number`)
      }

      return value as number
    })
  })

  function isRowSelectable(row: TableRow): boolean {
    return options?.isSelectable ? options.isSelectable(row) : true
  }

  function selectionColumn(): TableColumn<TableRow> {
    return {
      id: 'select',
      header: ({ table }) => {
        // вычисляем только те строки, которые разрешено выбирать
        const pageRows = table.getRowModel().rows
        const selectableRows = pageRows.filter((r) => isRowSelectable(r.original))

        const allSelected =
          selectableRows.length > 0 && selectableRows.every((r) => r.getIsSelected())
        const someSelected = selectableRows.some((r) => r.getIsSelected())

        return h(Checkbox, {
          modelValue: allSelected ? true : someSelected ? 'indeterminate' : false,
          'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
            // приводим к boolean: 'indeterminate' тоже трактуем как true при клике (браузер отдаёт true/false)
            const shouldSelect = !!value
            selectableRows.forEach((row) => row.toggleSelected(shouldSelect))
          },
          ariaLabel: 'Выбрать всё',
        })
      },
      cell: ({ row }) => {
        const selectable = isRowSelectable(row.original)

        if (!selectable && options?.renderNonSelectable) {
          return options.renderNonSelectable(row.original)
        }

        return h(Checkbox, {
          modelValue: row.getIsSelected(),
          disabled: !selectable,
          'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
            if (selectable) {
              row.toggleSelected(!!value)
            }
          },
          ariaLabel: 'Выбрать строку',
        })
      },
    }
  }

  return {
    tableApi,
    selectedIds,
    selectionColumn,
  }
}
