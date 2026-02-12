import { ref } from 'vue'
import { useUploadStore } from '@/stores/upload-store'
import { useApi } from '@/composables/use-api'

import type {
  AccountIn,
  AccountListOut,
  AccountOut,
  AccountStateOut,
  AccountsCheckIn,
  BindProjectIn,
  BuyPremiumOut,
  CardDetails,
  SetLimitIn,
  WorkflowOut,
} from '@/types/openapi'

export function useAccounts() {
  const accounts = ref<AccountOut[]>([])

  const { api, loading, error, success } = useApi()
  const { uploadOne } = useUploadStore()

  async function update(id: number, data: AccountIn): Promise<WorkflowOut> {
    const response = await api<WorkflowOut>(`accounts/${id}`, {
      method: 'PATCH',
      body: data,
    })
    return response
  }

  async function premium(id: number, body: CardDetails): Promise<BuyPremiumOut> {
    return await api<BuyPremiumOut>(`accounts/${id}/premium`, { method: 'POST', body })
  }

  async function stopPremium(id: number): Promise<WorkflowOut> {
    return await api<WorkflowOut>(`accounts/${id}/stop-premium`, { method: 'GET' })
  }

  async function del(ids: number[]) {
    const query = ids.map((id) => `id=${id}`).join('&')
    return await api(`accounts?${query}`, { method: 'DELETE' })
  }

  async function get(): Promise<AccountOut[]>
  async function get(id: number): Promise<AccountOut>
  async function get(id?: number): Promise<AccountOut | AccountOut[]> {
    if (id) {
      const response = await api<AccountOut>(`accounts/${id}`, { method: 'GET' })
      return response
    } else {
      const response = await api<AccountOut[]>('accounts', { method: 'GET' })
      accounts.value = response
      return response
    }
  }

  async function upload(file: File): Promise<WorkflowOut> {
    const fileMeta = await uploadOne(file, 'service')
    return await api<WorkflowOut>('accounts', {
      method: 'POST',
      body: { s3path: fileMeta.storagePath },
    })
  }

  async function bindProject(body: BindProjectIn) {
    return await api(`accounts/bind-project`, { method: 'POST', body })
  }

  async function setLimit(body: SetLimitIn) {
    return await api(`accounts/set-limit`, { method: 'POST', body })
  }

  async function check(body: AccountsCheckIn): Promise<WorkflowOut> {
    return await api(`accounts/check`, { method: 'POST', body })
  }

  async function list() {
    return await api<AccountListOut[]>('accounts/list', { method: 'GET' })
  }

  async function state() {
    return await api<AccountStateOut[]>('accounts/state', { method: 'GET' })
  }

  return {
    upload,
    premium,
    list,
    state,
    update,
    check,
    get,
    del,
    accounts,
    bindProject,
    setLimit,
    stopPremium,
    loading,
    error,
    success,
  }
}
