export interface StoryResponse {
  id: string
  title: string
  genre: string | null
  content_mode: 'unrestricted' | 'safe'
  auto_illustrate: boolean
  context_depth: number
  created_at: string
  updated_at: string
  current_leaf_id: string | null
}

export interface StoryCreate {
  title: string
  genre?: string | null
  content_mode?: 'unrestricted' | 'safe'
}

export interface StoryUpdate {
  content_mode?: 'unrestricted' | 'safe'
  auto_illustrate?: boolean
  context_depth?: number
}

export interface UnknownCharacter {
  name: string
  entity_type: string
  description: string
  base_prompt: string
}

export interface NodeResponse {
  id: string
  story_id: string
  parent_id: string | null
  content: string
  summary: string | null
  node_type: string
  created_at: string
  beat: Beat | null
  continuity_warnings: string[]
  unknown_characters: UnknownCharacter[]
  illustration_path: string | null
}

export interface Beat {
  setting?: string
  characters?: string[]
  conflict?: string
  tone?: string
  foreshadowing?: string
  [key: string]: unknown
}

export interface EntityResponse {
  id: string
  story_id: string
  entity_type: 'character' | 'location' | 'prop'
  name: string
  description: string
  base_prompt: string
  reference_image_path: string | null
  image_seed: number | null
  version: number
  created_at: string
}

export interface EntityCreate {
  entity_type: 'character' | 'location' | 'prop'
  name: string
  description: string
  base_prompt: string
}

export interface EntityUpdate {
  description?: string
  base_prompt?: string
}

export interface ImageSelectRequest {
  filename: string
  seed: number
  reject_filenames: string[]
}

export interface ContinuityIssue {
  scene: number
  issue: string
  severity: 'warning' | 'error'
}

export interface ContinuityCheckResponse {
  issues: ContinuityIssue[]
  scene_count: number
}
