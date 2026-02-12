import { useState, useRef, useEffect } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import { exportMarkdownUrl, exportEpubUrl } from '../../api/stories'
import styles from '../../styles/components/Header.module.css'

export default function Header() {
  const currentStory = useStoryStore((s) => s.currentStory)
  const closeStory = useStoryStore((s) => s.closeStory)
  const setView = useUiStore((s) => s.setView)
  const setShowSettingsPanel = useUiStore((s) => s.setShowSettingsPanel)
  const showSettingsPanel = useUiStore((s) => s.showSettingsPanel)

  const [exportOpen, setExportOpen] = useState(false)
  const exportRef = useRef<HTMLDivElement>(null)

  const handleBack = () => {
    closeStory()
    setView('lobby')
  }

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false)
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [])

  if (!currentStory) return null

  return (
    <header className={styles.header}>
      <button className="btn btn-ghost" onClick={handleBack}>Back</button>
      <h1>{currentStory.title}</h1>
      <div className={styles.actions}>
        <div className={styles.exportWrapper} ref={exportRef}>
          <button
            className="btn btn-small"
            onClick={(e) => { e.stopPropagation(); setExportOpen(!exportOpen) }}
          >
            Export
          </button>
          {exportOpen && (
            <div className={styles.exportDropdown}>
              <button
                className={styles.exportOption}
                onClick={() => { window.open(exportMarkdownUrl(currentStory.id), '_blank'); setExportOpen(false) }}
              >
                Markdown
              </button>
              <button
                className={styles.exportOption}
                onClick={() => { window.open(exportEpubUrl(currentStory.id), '_blank'); setExportOpen(false) }}
              >
                EPUB
              </button>
            </div>
          )}
        </div>
        <button
          className={`btn btn-small ${showSettingsPanel ? 'btn-primary' : ''}`}
          onClick={() => setShowSettingsPanel(!showSettingsPanel)}
        >
          Settings
        </button>
      </div>
    </header>
  )
}
