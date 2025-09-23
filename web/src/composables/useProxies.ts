import { ref } from "vue";

import { useApi } from "@/composables/useApi";
import { useUploadStore } from "@/stores/upload";

interface UploadOptions {
  file?: File
  text?: string
}


export function useProxies () {

  const proxies = ref<Proxy[]>([])
  const { api, loading, error, success } = useApi()
  const { uploadOne } = useUploadStore()


  async function del (ids: number[]) {
    const query = ids.map(id => `id=${id}`).join('&')
    return await api(`proxies?${query}`, { method: "DELETE" })
  }

  async function get (): Promise<Proxy[]> {
    const data = await api<Proxy[]>('proxies', {
      method: "GET"
    })
    proxies.value = data
    return data
  }

  async function upload ({ text, file }: UploadOptions): Promise<Workflow> {
    if (!file && !text) {
      throw new Error('Either file or text must be provided')
    }
    const fileToUpload: File = file ?? new File([text!], 'proxies.txt', { type: 'text/plain' })

    const s3path = await uploadOne(fileToUpload, 'service')

    return await api<Workflow>('proxies', {
      method: "POST",
      body: { s3path },
    })
  }


  return { upload, get, del, proxies, loading, error, success }

}
