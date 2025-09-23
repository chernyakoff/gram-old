import { defineStore } from 'pinia'
import { reactive } from 'vue'


export const useBackgroundJobs = defineStore("backgroundJobs", () => {
  const jobs = reactive<BackgroundJob[]>([])

  function add (job: {
    id: string
    name: string
    status?: BackgroundJob["status"]
    logs?: LogEntry[]
    onComplete?: (job: BackgroundJob) => void
  }) {
    jobs.push({
      id: job.id,
      name: job.name,
      status: job.status ?? "pending",
      logs: job.logs ?? [],
      createdAt: new Date(),
      onComplete: job.onComplete,
    })
  }

  function update (id: string, update: Partial<BackgroundJob>) {
    const job = jobs.find((j) => j.id === id)
    if (job) {
      Object.assign(job, update)
      if (
        ["finished", "failed"].includes(update.status ?? "") &&
        job.onComplete
      ) {
        job.onComplete(job)
      }
    }
  }

  function getJob (id: string) {
    return jobs.find((j) => j.id === id)
  }

  function addLog (id: string, log: LogEntry) {
    const job = getJob(id)
    if (job) job.logs.push(log)
  }

  function setOnComplete (id: string, callback: (job: BackgroundJob) => void) {
    const job = getJob(id)
    if (job) job.onComplete = callback
  }

  return { jobs, add, update, getJob, addLog, setOnComplete }
})
