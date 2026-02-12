import { create } from 'zustand'
import type { StoryResponse, NodeResponse, EntityResponse, StoryUpdate, EntityCreate, EntityUpdate } from '../types/api'
import * as storiesApi from '../api/stories'
import * as nodesApi from '../api/nodes'
import * as entitiesApi from '../api/entities'

interface StoryState {
  // Story list
  stories: StoryResponse[]
  fetchStories: () => Promise<void>
  createStory: (title: string, genre: string | null, contentMode: 'unrestricted' | 'safe') => Promise<StoryResponse>
  deleteStory: (id: string) => Promise<void>

  // Current story
  currentStory: StoryResponse | null
  currentLeafId: string | null
  openStory: (story: StoryResponse) => void
  closeStory: () => void
  updateStorySettings: (id: string, updates: StoryUpdate) => Promise<void>

  // Nodes
  allNodes: NodeResponse[]
  pathNodes: NodeResponse[]
  loadPath: (leafId: string) => Promise<void>
  loadTree: (storyId: string) => Promise<void>
  navigateToNode: (nodeId: string) => Promise<void>
  appendNode: (node: NodeResponse) => void
  updateNodeIllustration: (nodeId: string, path: string) => void

  // Entities
  entities: EntityResponse[]
  fetchEntities: (storyId: string) => Promise<void>
  createEntity: (storyId: string, data: EntityCreate) => Promise<EntityResponse>
  updateEntity: (entityId: string, updates: EntityUpdate) => Promise<EntityResponse>
  replaceEntity: (entity: EntityResponse) => void
}

export const useStoryStore = create<StoryState>((set, _get) => ({
  stories: [],
  fetchStories: async () => {
    const stories = await storiesApi.listStories()
    set({ stories })
  },
  createStory: async (title, genre, contentMode) => {
    const story = await storiesApi.createStory({ title, genre, content_mode: contentMode })
    set((s) => ({ stories: [story, ...s.stories] }))
    return story
  },
  deleteStory: async (id) => {
    await storiesApi.deleteStory(id)
    set((s) => ({ stories: s.stories.filter((st) => st.id !== id) }))
  },

  currentStory: null,
  currentLeafId: null,
  openStory: (story) => set({ currentStory: story, currentLeafId: story.current_leaf_id }),
  closeStory: () => set({ currentStory: null, currentLeafId: null, allNodes: [], pathNodes: [], entities: [] }),
  updateStorySettings: async (id, updates) => {
    const updated = await storiesApi.updateStory(id, updates)
    set({ currentStory: updated })
  },

  allNodes: [],
  pathNodes: [],
  loadPath: async (leafId) => {
    const pathNodes = await nodesApi.getNodePath(leafId)
    set({ pathNodes, currentLeafId: leafId })
  },
  loadTree: async (storyId) => {
    const allNodes = await storiesApi.getStoryTree(storyId)
    set({ allNodes })
  },
  navigateToNode: async (nodeId) => {
    const pathNodes = await nodesApi.getNodePath(nodeId)
    set({ pathNodes, currentLeafId: nodeId })
  },
  appendNode: (node) => {
    set((s) => ({
      pathNodes: [...s.pathNodes, node],
      allNodes: [...s.allNodes, node],
      currentLeafId: node.id,
      currentStory: s.currentStory ? { ...s.currentStory, current_leaf_id: node.id } : null,
    }))
  },
  updateNodeIllustration: (nodeId, path) => {
    set((s) => ({
      pathNodes: s.pathNodes.map((n) => n.id === nodeId ? { ...n, illustration_path: path } : n),
      allNodes: s.allNodes.map((n) => n.id === nodeId ? { ...n, illustration_path: path } : n),
    }))
  },

  entities: [],
  fetchEntities: async (storyId) => {
    const entities = await entitiesApi.listEntities(storyId)
    set({ entities })
  },
  createEntity: async (storyId, data) => {
    const entity = await entitiesApi.createEntity(storyId, data)
    set((s) => ({ entities: [...s.entities, entity] }))
    return entity
  },
  updateEntity: async (entityId, updates) => {
    const entity = await entitiesApi.updateEntity(entityId, updates)
    set((s) => ({ entities: s.entities.map((e) => e.id === entity.id ? entity : e) }))
    return entity
  },
  replaceEntity: (entity) => {
    set((s) => ({ entities: s.entities.map((e) => e.id === entity.id ? entity : e) }))
  },
}))
