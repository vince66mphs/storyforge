import { useState, useEffect } from 'react'
import { useUiStore } from '../../store/uiStore'
import { useStoryStore } from '../../store/storyStore'
import { checkContinuity } from '../../api/stories'
import type { ContinuityCheckResponse } from '../../types/api'
import Spinner from '../shared/Spinner'
import styles from '../../styles/components/ContinuityCheckModal.module.css'

export default function ContinuityCheckModal() {
  const show = useUiStore((s) => s.showContinuityModal)
  const close = useUiStore((s) => s.setShowContinuityModal)
  const currentStory = useStoryStore((s) => s.currentStory)
  const addToast = useUiStore((s) => s.addToast)

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ContinuityCheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!show || !currentStory) return
    setLoading(true)
    setResult(null)
    setError(null)

    checkContinuity(currentStory.id)
      .then(setResult)
      .catch((err) => {
        const msg = err instanceof Error ? err.message : 'Check failed'
        setError(msg)
        addToast(msg, 'error')
      })
      .finally(() => setLoading(false))
  }, [show, currentStory, addToast])

  useEffect(() => {
    if (!show) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [show, close])

  if (!show) return null

  return (
    <div className={styles.overlay} onClick={() => close(false)}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>Continuity Check</h3>
          <button className={styles.closeBtn} onClick={() => close(false)}>&times;</button>
        </div>
        <div className={styles.body}>
          {loading && (
            <div className={styles.loading}>
              <Spinner /> Analyzing story continuity...
            </div>
          )}
          {error && (
            <div className={styles.error}>{error}</div>
          )}
          {result && result.issues.length === 0 && (
            <div className={styles.clean}>No continuity issues found across {result.scene_count} scenes.</div>
          )}
          {result && result.issues.length > 0 && (
            <>
              <div className={styles.summary}>
                Found {result.issues.length} issue{result.issues.length !== 1 ? 's' : ''} across {result.scene_count} scenes
              </div>
              <div className={styles.issues}>
                {result.issues.map((issue, i) => (
                  <div key={i} className={`${styles.issue} ${issue.severity === 'error' ? styles.issueError : styles.issueWarning}`}>
                    <span className={styles.badge}>{issue.severity}</span>
                    <span className={styles.scene}>S{issue.scene}</span>
                    <span className={styles.issueText}>{issue.issue}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
