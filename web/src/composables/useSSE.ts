import { useBackgroundJobs } from '@/stores/jobs'

let evtSource: EventSource | null = null

export function useSSE () {
  const store = useBackgroundJobs()

  function connect () {
    if (evtSource) return // уже подключен

    evtSource = new EventSource(`${import.meta.env.API_URL}/sse`)

    evtSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.log) {
        store.addLog(data.jobId, data.log)

        // первый лог → переводим задачу в running
        const job = store.getJob(data.jobId)
        if (job && job.status === "pending") {
          store.update(data.jobId, { status: "running" })
        }
      }

      if (data.status) {
        store.update(data.jobId, { status: data.status })
      }
    }

    evtSource.addEventListener('ping', () => {
      console.debug('ping')
    })

    evtSource.onerror = () => {
      console.warn('SSE disconnected, retrying in 3s...')
      disconnect()
      setTimeout(connect, 3000) // авто-переподключение
    }
  }

  function disconnect () {
    if (evtSource) {
      evtSource.close()
      evtSource = null
    }
  }

  return { connect, disconnect }
}
