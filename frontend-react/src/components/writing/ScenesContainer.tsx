import { useRef, useEffect } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import Scene from './Scene'
import styles from '../../styles/components/Scenes.module.css'

export default function ScenesContainer() {
  const pathNodes = useStoryStore((s) => s.pathNodes)
  const isGenerating = useUiStore((s) => s.isGenerating)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new scenes appear or during generation
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [pathNodes.length, isGenerating])

  return (
    <div className={styles.container} ref={containerRef}>
      {pathNodes.map((node) => (
        <Scene key={node.id} node={node} />
      ))}
    </div>
  )
}
