import { create } from 'zustand'
import type { EntityResponse } from '../types/api'

export interface Toast {
  id: number
  message: string
  type: 'info' | 'error' | 'success'
}

let nextToastId = 0

interface UiState {
  view: 'lobby' | 'writing'
  setView: (view: 'lobby' | 'writing') => void

  // Generation state
  isGenerating: boolean
  generatingPhase: 'planning' | 'writing' | null
  streamContent: string
  setGenerating: (generating: boolean) => void
  setPhase: (phase: 'planning' | 'writing' | null) => void
  appendToken: (text: string) => void
  resetStream: () => void

  // Modals
  entityDetailEntity: EntityResponse | null
  imageGridEntityId: string | null
  lightboxSrc: string | null
  lightboxCaption: string | null
  showContinuityModal: boolean
  showSettingsPanel: boolean

  openEntityDetail: (entity: EntityResponse) => void
  closeEntityDetail: () => void
  openImageGrid: (entityId: string) => void
  closeImageGrid: () => void
  openLightbox: (src: string, caption?: string) => void
  closeLightbox: () => void
  setShowContinuityModal: (show: boolean) => void
  setShowSettingsPanel: (show: boolean) => void

  // Toasts
  toasts: Toast[]
  addToast: (message: string, type?: 'info' | 'error' | 'success') => void
  removeToast: (id: number) => void
}

export const useUiStore = create<UiState>((set) => ({
  view: 'lobby',
  setView: (view) => set({ view }),

  isGenerating: false,
  generatingPhase: null,
  streamContent: '',
  setGenerating: (isGenerating) => set({ isGenerating }),
  setPhase: (generatingPhase) => set({ generatingPhase }),
  appendToken: (text) => set((s) => ({ streamContent: s.streamContent + text })),
  resetStream: () => set({ streamContent: '', isGenerating: false, generatingPhase: null }),

  entityDetailEntity: null,
  imageGridEntityId: null,
  lightboxSrc: null,
  lightboxCaption: null,
  showContinuityModal: false,
  showSettingsPanel: false,

  openEntityDetail: (entity) => set({ entityDetailEntity: entity }),
  closeEntityDetail: () => set({ entityDetailEntity: null }),
  openImageGrid: (entityId) => set({ imageGridEntityId: entityId }),
  closeImageGrid: () => set({ imageGridEntityId: null }),
  openLightbox: (src, caption) => set({ lightboxSrc: src, lightboxCaption: caption ?? null }),
  closeLightbox: () => set({ lightboxSrc: null, lightboxCaption: null }),
  setShowContinuityModal: (show) => set({ showContinuityModal: show }),
  setShowSettingsPanel: (show) => set({ showSettingsPanel: show }),

  toasts: [],
  addToast: (message, type = 'info') => {
    const id = nextToastId++
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 4000)
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
