import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import ContentModeToggle from '../shared/ContentModeToggle'
import styles from '../../styles/components/SettingsPanel.module.css'

export default function SettingsPanel() {
  const currentStory = useStoryStore((s) => s.currentStory)
  const updateStorySettings = useStoryStore((s) => s.updateStorySettings)
  const setShowContinuityModal = useUiStore((s) => s.setShowContinuityModal)
  const addToast = useUiStore((s) => s.addToast)

  if (!currentStory) return null

  const handleContentMode = async (mode: 'unrestricted' | 'safe') => {
    try {
      await updateStorySettings(currentStory.id, { content_mode: mode })
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to update settings', 'error')
    }
  }

  const handleAutoIllustrate = async (enabled: boolean) => {
    try {
      await updateStorySettings(currentStory.id, { auto_illustrate: enabled })
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to update settings', 'error')
    }
  }

  const handleContextDepth = async (depth: number) => {
    try {
      await updateStorySettings(currentStory.id, { context_depth: depth })
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to update settings', 'error')
    }
  }

  return (
    <div className={styles.panel}>
      <h4>Settings</h4>

      <div className={styles.group}>
        <label>Content Mode</label>
        <ContentModeToggle value={currentStory.content_mode} onChange={handleContentMode} />
      </div>

      <div className={styles.group}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={currentStory.auto_illustrate}
            onChange={(e) => handleAutoIllustrate(e.target.checked)}
          />
          Auto-Illustrate
        </label>
      </div>

      <div className={styles.group}>
        <label>Context Depth</label>
        <div className={styles.slider}>
          <input
            type="range"
            min={1}
            max={20}
            value={currentStory.context_depth}
            onChange={(e) => handleContextDepth(Number(e.target.value))}
          />
          <span>{currentStory.context_depth}</span>
        </div>
      </div>

      <div className={`${styles.group} ${styles.divider}`}>
        <button
          className="btn btn-secondary btn-small"
          onClick={() => setShowContinuityModal(true)}
        >
          Continuity Check
        </button>
      </div>
    </div>
  )
}
