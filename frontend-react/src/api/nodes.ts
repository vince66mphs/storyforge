import { request } from './client'
import type { NodeResponse } from '../types/api'

export function generateScene(storyId: string, userPrompt: string) {
  return request<NodeResponse>('POST', `/api/stories/${storyId}/nodes`, { user_prompt: userPrompt })
}

export function getNode(nodeId: string) {
  return request<NodeResponse>('GET', `/api/nodes/${nodeId}`)
}

export function getNodePath(nodeId: string) {
  return request<NodeResponse[]>('GET', `/api/nodes/${nodeId}/path`)
}

export function createBranch(nodeId: string, userPrompt: string) {
  return request<NodeResponse>('POST', `/api/nodes/${nodeId}/branch`, { user_prompt: userPrompt })
}

export function illustrateNode(nodeId: string) {
  return request<NodeResponse>('POST', `/api/nodes/${nodeId}/illustrate`)
}
