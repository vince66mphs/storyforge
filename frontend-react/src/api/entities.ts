import { request, ApiError } from './client'
import type { EntityResponse, EntityCreate, EntityUpdate, ImageSelectRequest } from '../types/api'

export function listEntities(storyId: string) {
  return request<EntityResponse[]>('GET', `/api/stories/${storyId}/entities`)
}

export function createEntity(storyId: string, data: EntityCreate) {
  return request<EntityResponse>('POST', `/api/stories/${storyId}/entities`, data)
}

export function detectEntities(storyId: string, text: string) {
  return request<EntityResponse[]>('POST', `/api/stories/${storyId}/entities/detect`, { text })
}

export function getEntity(entityId: string) {
  return request<EntityResponse>('GET', `/api/entities/${entityId}`)
}

export function updateEntity(entityId: string, updates: EntityUpdate) {
  return request<EntityResponse>('PATCH', `/api/entities/${entityId}`, updates)
}

export function generateEntityImage(entityId: string) {
  return request<EntityResponse>('POST', `/api/entities/${entityId}/image`)
}

export function selectEntityImage(entityId: string, data: ImageSelectRequest) {
  return request<EntityResponse>('POST', `/api/entities/${entityId}/images/select`, data)
}

export function generateEntityImagesUrl(entityId: string) {
  return `/api/entities/${entityId}/images/generate`
}

export function describeEntityFromImage(entityId: string) {
  return request<EntityResponse>('POST', `/api/entities/${entityId}/describe`)
}

export async function uploadEntityImage(entityId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)

  let res: Response
  try {
    res = await fetch(`/api/entities/${entityId}/image/upload`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new ApiError(0, 'Network error — server may be down', 'network_error')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<EntityResponse>
}
