import { useState, useCallback } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/PromptArea.module.css'

interface Props {
  socket: {
    generate: (storyId: string, prompt: string, parentNodeId?: string) => void
    branch: (storyId: string, nodeId: string, prompt: string) => void
  }
}

export default function PromptArea({ socket }: Props) {
  const [prompt, setPrompt] = useState('')
  const currentStory = useStoryStore((s) => s.currentStory)
  const currentLeafId = useStoryStore((s) => s.currentLeafId)
  const isGenerating = useUiStore((s) => s.isGenerating)

  const handleContinue = useCallback(() => {
    if (!currentStory || isGenerating) return
    const text = prompt.trim() || 'Continue the story.'
    socket.generate(currentStory.id, text, currentLeafId ?? undefined)
    setPrompt('')
  }, [currentStory, currentLeafId, isGenerating, prompt, socket])

  const handleBranch = useCallback(() => {
    if (!currentStory || !currentLeafId || isGenerating) return
    const text = prompt.trim() || 'Take the story in a different direction.'
    socket.branch(currentStory.id, currentLeafId, text)
    setPrompt('')
  }, [currentStory, currentLeafId, isGenerating, prompt, socket])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleContinue()
    }
  }

  return (
    <div className={styles.area}>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What happens next? (Ctrl+Enter to continue)"
        rows={3}
        disabled={isGenerating}
      />
      <div className={styles.actions}>
        {currentLeafId && (
          <button
            className="btn btn-secondary"
            onClick={handleBranch}
            disabled={isGenerating}
          >
            Branch
          </button>
        )}
        <button
          className="btn btn-primary"
          onClick={handleContinue}
          disabled={isGenerating}
        >
          {currentLeafId ? 'Continue' : 'Begin Story'}
        </button>
      </div>
    </div>
  )
}
