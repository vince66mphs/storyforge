import { useRef, useEffect } from 'react'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/StreamingScene.module.css'

export default function StreamingScene() {
  const streamContent = useUiStore((s) => s.streamContent)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [streamContent])

  if (!streamContent) return null

  return (
    <div className={styles.scene} ref={ref}>
      <div className={styles.meta}>Generating...</div>
      <div className={styles.content}>
        {streamContent}
        <span className={styles.cursor} />
      </div>
    </div>
  )
}
