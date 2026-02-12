import type { NodeResponse } from './api'

// Messages sent from client to server
export interface GenerateMessage {
  action: 'generate'
  story_id: string
  prompt: string
  parent_node_id?: string
}

export interface BranchMessage {
  action: 'branch'
  story_id: string
  node_id: string
  prompt: string
}

export type ClientMessage = GenerateMessage | BranchMessage

// Messages received from server
export interface TokenMessage {
  type: 'token'
  content: string
}

export interface PhaseMessage {
  type: 'phase'
  phase: 'planning' | 'writing'
}

export interface CompleteMessage {
  type: 'complete'
  node: NodeResponse
}

export interface IllustrationMessage {
  type: 'illustration'
  node_id: string
  path: string
}

export interface ErrorMessage {
  type: 'error'
  message: string
  error_type?: string
  service?: string
}

export type ServerMessage =
  | TokenMessage
  | PhaseMessage
  | CompleteMessage
  | IllustrationMessage
  | ErrorMessage
