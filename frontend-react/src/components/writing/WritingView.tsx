import { useEffect, useCallback } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import Header from '../layout/Header'
import WritingLayout from '../layout/WritingLayout'
import useStorySocket from '../../hooks/useStorySocket'
import styles from '../../styles/components/WritingView.module.css'

export default function WritingView() {
  const currentStory = useStoryStore((s) => s.currentStory)
  const loadPath = useStoryStore((s) => s.loadPath)
  const loadTree = useStoryStore((s) => s.loadTree)
  const fetchEntities = useStoryStore((s) => s.fetchEntities)
  const appendNode = useStoryStore((s) => s.appendNode)
  const updateNodeIllustration = useStoryStore((s) => s.updateNodeIllustration)
  const addToast = useUiStore((s) => s.addToast)
  const setGenerating = useUiStore((s) => s.setGenerating)
  const setPhase = useUiStore((s) => s.setPhase)
  const appendToken = useUiStore((s) => s.appendToken)
  const resetStream = useUiStore((s) => s.resetStream)

  const handleComplete = useCallback((node: Parameters<typeof appendNode>[0]) => {
    appendNode(node)
    resetStream()
    // Read currentStory from store at call time to avoid stale closure
    const story = useStoryStore.getState().currentStory
    if (story) {
      loadTree(story.id)
      fetchEntities(story.id)
    }
  }, [appendNode, resetStream, loadTree, fetchEntities])

  const handleIllustration = useCallback((nodeId: string, path: string) => {
    updateNodeIllustration(nodeId, path)
  }, [updateNodeIllustration])

  const handleError = useCallback((message: string) => {
    addToast(message, 'error')
    resetStream()
  }, [addToast, resetStream])

  const socket = useStorySocket({
    onToken: appendToken,
    onPhase: setPhase,
    onComplete: handleComplete,
    onIllustration: handleIllustration,
    onError: handleError,
    onGenerating: setGenerating,
  })

  // Load story data on mount
  useEffect(() => {
    if (!currentStory) return
    const init = async () => {
      if (currentStory.current_leaf_id) {
        await loadPath(currentStory.current_leaf_id)
      }
      await loadTree(currentStory.id)
      await fetchEntities(currentStory.id)

      // Check for opening prompt from create flow
      const openingPrompt = sessionStorage.getItem('openingPrompt')
      if (openingPrompt) {
        sessionStorage.removeItem('openingPrompt')
        socket.generate(currentStory.id, openingPrompt)
      }
    }
    init()
  }, [currentStory?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!currentStory) return null

  return (
    <div className={styles.view}>
      <Header />
      <WritingLayout socket={socket} />
    </div>
  )
}
