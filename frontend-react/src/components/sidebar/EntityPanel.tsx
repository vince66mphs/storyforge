import { useState } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import { detectEntities } from '../../api/entities'
import EntityItem from './EntityItem'
import AddEntityForm from './AddEntityForm'
import styles from '../../styles/components/EntityPanel.module.css'

export default function EntityPanel() {
  const [showAddForm, setShowAddForm] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const entities = useStoryStore((s) => s.entities)
  const currentStory = useStoryStore((s) => s.currentStory)
  const pathNodes = useStoryStore((s) => s.pathNodes)
  const fetchEntities = useStoryStore((s) => s.fetchEntities)
  const addToast = useUiStore((s) => s.addToast)

  const handleDetect = async () => {
    if (!currentStory || detecting) return
    const lastNode = pathNodes[pathNodes.length - 1]
    if (!lastNode) {
      addToast('No scene to detect entities from', 'error')
      return
    }

    setDetecting(true)
    try {
      await detectEntities(currentStory.id, lastNode.content)
      await fetchEntities(currentStory.id)
      addToast('Entity detection complete', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Detection failed', 'error')
    } finally {
      setDetecting(false)
    }
  }

  // Group entities by type
  const grouped = entities.reduce<Record<string, typeof entities>>((acc, e) => {
    const key = e.entity_type
    if (!acc[key]) acc[key] = []
    acc[key]!.push(e)
    return acc
  }, {})

  return (
    <div className={styles.section}>
      <h3>World Bible</h3>
      <div className={styles.actions}>
        <button
          className="btn btn-small btn-secondary"
          onClick={handleDetect}
          disabled={detecting}
        >
          {detecting ? 'Detecting...' : 'Detect'}
        </button>
        <button
          className="btn btn-small btn-ghost"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? 'Cancel' : 'Add'}
        </button>
      </div>

      {showAddForm && <AddEntityForm onDone={() => setShowAddForm(false)} />}

      <div className={styles.list}>
        {Object.entries(grouped).map(([type, items]) => (
          <div key={type}>
            <div className={styles.typeLabel}>{type}s</div>
            {items.map((entity) => (
              <EntityItem key={entity.id} entity={entity} />
            ))}
          </div>
        ))}
        {entities.length === 0 && (
          <div className={styles.empty}>No entities yet</div>
        )}
      </div>
    </div>
  )
}
