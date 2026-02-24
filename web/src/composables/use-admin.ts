import { useApi } from '@/composables/use-api'
import type {
  AppSettingIn,
  BalanceIn,
  BalanceOut,
  DialogsDownloadIn,
  GetBalanceOut,
  LicenseIn,
  LicenseOut,
} from '@/types/openapi'

export function useAdmin() {
  const { api, apiUsers, apiBlob, loading, error, success } = useApi()

  async function license(body: LicenseIn) {
    return await apiUsers<LicenseOut>(`admin/license`, { method: 'POST', body })
  }

  async function addBalance(body: BalanceIn): Promise<BalanceOut> {
    return await apiUsers<BalanceOut>(`admin/balance`, { method: 'POST', body })
  }

  async function getBalance(): Promise<GetBalanceOut> {
    return await api<GetBalanceOut>(`admin/balance`, { method: 'GET' })
  }

  async function getAppSetting(path: string): Promise<string> {
    return await api(`admin/app-setting/${path}`, { method: 'GET' })
  }

  async function saveAppSetting(body: AppSettingIn): Promise<string> {
    return await api('admin/app-setting', { method: 'POST', body })
  }

  async function downloadDialogs(body: DialogsDownloadIn) {
    try {
      console.time('Total download time')
      console.time('API call')

      const blob = await apiBlob('admin/dialogs', { method: 'POST', body })

      console.timeEnd('API call')
      console.log('Blob size:', blob.size, 'bytes')
      console.time('File creation')

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dialogs_${body.username}.json`
      document.body.appendChild(a)
      a.click()

      console.timeEnd('File creation')
      console.timeEnd('Total download time')

      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Ошибка при скачивании:', e)
    }
  }

  return {
    license,
    getAppSetting,
    saveAppSetting,
    addBalance,
    getBalance,
    downloadDialogs,
    loading,
    error,
    success,
  }
}
