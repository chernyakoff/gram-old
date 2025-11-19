import { useApi } from '@/composables/use-api'

import type {
  ProjectBase,
  ProjectIn,
  ProjectOut,
  ProjectShortOut,
  WorkflowOut,
} from '@/types/openapi'
import { ref } from 'vue'

export function useProjects() {
  const projects = ref<ProjectShortOut[]>([])
  const { api, loading, error, success } = useApi()

  async function del(ids: number[]) {
    const query = ids.map((id) => `id=${id}`).join('&')
    return await api(`projects?${query}`, { method: 'DELETE' })
  }

  async function get(): Promise<ProjectShortOut[]>
  async function get(id: number): Promise<ProjectOut>
  async function get(id?: number) {
    if (id) {
      return await api<ProjectOut>(`projects/${id}`, { method: 'GET' })
    } else {
      const data = await api<ProjectShortOut[]>('projects', { method: 'GET' })
      projects.value = data
      return data
    }
  }
  async function default_project() {
    return await api<ProjectIn>('projects/default', { method: 'GET' })
  }

  async function list() {
    return await api<ProjectBase[]>('projects/list', { method: 'GET' })
  }

  async function status(id: number, value: boolean) {
    return await api(`projects/${id}/status`, { method: 'PATCH', body: { status: value } })
  }

  async function update(id: number, body: ProjectIn) {
    return await api<WorkflowOut>(`projects/${id}`, {
      method: 'PATCH',
      body,
    })
  }

  async function create(body: ProjectIn) {
    return await api<WorkflowOut>('projects', {
      method: 'POST',
      body,
    })
  }

  return {
    create,
    get,
    del,
    update,
    projects,
    status,
    list,
    default_project,
    loading,
    error,
    success,
  }
}
