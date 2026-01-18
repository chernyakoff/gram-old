import { useApi } from '@/composables/use-api'

import type {
  Brief,
  ProjectBase,
  ProjectCreateIn,
  ProjectFileIn,
  ProjectFileOut,
  ProjectFileUpdateIn,
  ProjectSettings,
  ProjectShortOut,
  ProjectStatusOut,
  Prompt,
  SynonimizeIn,
  SynonimizeOut,
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

  async function get(): Promise<ProjectShortOut[]> {
    const data = await api<ProjectShortOut[]>('projects', { method: 'GET' })
    projects.value = data
    return data
  }

  async function list() {
    return await api<ProjectBase[]>('projects/list', { method: 'GET' })
  }

  async function status(id: number, value: boolean) {
    return await api<ProjectStatusOut>(`projects/${id}/status`, {
      method: 'PATCH',
      body: { status: value },
    })
  }

  async function synonimize(body: SynonimizeIn) {
    return await api<SynonimizeOut>(`projects/synonimize`, {
      method: 'POST',
      body,
    })
  }

  /* async function uploadEmbed(body: ProjectFilesIn): Promise<WorkflowOut> {
    return await api<WorkflowOut>(`projects/upload-embed`, {
      method: 'POST',
      body,
    })
  } */

  async function createProject(body: ProjectCreateIn) {
    return await api('projects/create', {
      method: 'POST',
      body,
    })
  }

  async function saveSettings(id: number, body: ProjectSettings) {
    return await api(`projects/${id}/settings`, {
      method: 'POST',
      body,
    })
  }

  async function getSettings(id: number) {
    return await api<ProjectSettings>(`projects/${id}/settings`, {
      method: 'GET',
    })
  }

  async function saveBrief(id: number, body: Brief) {
    return await api(`projects/${id}/brief`, {
      method: 'POST',
      body,
    })
  }

  async function getBrief(id: number) {
    return await api<Brief>(`projects/${id}/brief`, {
      method: 'GET',
    })
  }

  async function savePrompt(id: number, body: Prompt) {
    return await api(`projects/${id}/prompt`, {
      method: 'POST',
      body,
    })
  }

  async function getPrompt(id: number) {
    return await api<Prompt>(`projects/${id}/prompt`, {
      method: 'GET',
    })
  }

  async function generatePrompt(id: number, body: Brief) {
    return await api<WorkflowOut>(`projects/${id}/generate-prompt`, {
      method: 'POST',
      body,
    })
  }

  async function saveFiles(id: number, body: ProjectFileIn[]) {
    return await api(`projects/${id}/files`, {
      method: 'POST',
      body,
    })
  }

  async function getFiles(id: number) {
    return await api<ProjectFileOut[]>(`projects/${id}/files`, {
      method: 'GET',
    })
  }

  async function deleteFile(projectId: number, fileId: number) {
    return await api(`projects/${projectId}/files/${fileId}`, { method: 'DELETE' })
  }

  async function updateFile(projectId: number, fileId: number, body: ProjectFileUpdateIn) {
    return await api(`projects/${projectId}/files/${fileId}`, { method: 'POST', body })
  }

  return {
    get,
    del,

    synonimize,
    projects,
    status,
    list,
    createProject,
    saveSettings,
    getSettings,
    saveBrief,
    getBrief,
    savePrompt,
    getPrompt,
    generatePrompt,
    saveFiles,
    getFiles,
    deleteFile,
    updateFile,
    loading,
    error,
    success,
  }
}
