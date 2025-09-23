import { ref } from "vue";
import { useUploadStore } from "@/stores/upload";
import { useApi } from "@/composables/useApi";
import type { AccountUpdatePayload } from "@/schemas/account";


export function useAccounts () {

  const accounts = ref<Account[]>([])
  const { api, loading, error, success } = useApi()
  const { uploadOne } = useUploadStore()

  async function update (id: number, data: AccountUpdatePayload): Promise<Workflow> {
    const response = await api<Workflow>(`accounts/${id}`, {
      method: 'PATCH',
      body: data
    })
    return response
  }

  async function del (ids: number[]) {
    const query = ids.map(id => `id=${id}`).join('&')
    return await api(`accounts?${query}`, { method: "DELETE" })
  }

  async function get (): Promise<Account[]>
  async function get (id: number): Promise<Account>
  async function get (id?: number): Promise<Account | Account[]> {
    if (id) {
      const response = await api<Account>(`accounts/${id}`, { method: 'GET' })
      return response
    } else {
      const response = await api<Account[]>('accounts', { method: 'GET' })
      accounts.value = response
      return response
    }
  }

  async function upload (file: File): Promise<Workflow> {
    const s3path = await uploadOne(file, 'service')
    return await api<Workflow>('accounts', {
      method: 'POST',
      body: { s3path },
    })
  }

  return { upload, update, get, del, accounts, loading, error, success }

}
