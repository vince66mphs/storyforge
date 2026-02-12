import { request } from './client'
import type { StoryResponse, StoryCreate, StoryUpdate, NodeResponse, ContinuityCheckResponse } from '../types/api'

export function listStories() {
  return request<StoryResponse[]>('GET', '/api/stories')
}

export function getStory(id: string) {
  return request<StoryResponse>('GET', `/api/stories/${id}`)
}

export function createStory(data: StoryCreate) {
  return request<StoryResponse>('POST', '/api/stories', {
    title: data.title,
    genre: data.genre || null,
    content_mode: data.content_mode || 'unrestricted',
  })
}

export function updateStory(id: string, updates: StoryUpdate) {
  return request<StoryResponse>('PATCH', `/api/stories/${id}`, updates)
}

export function deleteStory(id: string) {
  return request<null>('DELETE', `/api/stories/${id}`)
}

export function getStoryTree(storyId: string) {
  return request<NodeResponse[]>('GET', `/api/stories/${storyId}/tree`)
}

export function checkContinuity(storyId: string) {
  return request<ContinuityCheckResponse>('POST', `/api/stories/${storyId}/check-continuity`)
}

export function exportMarkdownUrl(storyId: string) {
  return `/api/stories/${storyId}/export/markdown`
}

export function exportEpubUrl(storyId: string) {
  return `/api/stories/${storyId}/export/epub`
}
