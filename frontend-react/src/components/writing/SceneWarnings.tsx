import { useState } from 'react'
import type { UnknownCharacter } from '../../types/api'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/SceneWarnings.module.css'

interface Props {
  warnings: string[]
  unknownCharacters: UnknownCharacter[]
  storyId: string
}

export default function SceneWarnings({ warnings, unknownCharacters, storyId }: Props) {
  const [addedNames, setAddedNames] = useState<Set<string>>(new Set())
  const [addingName, setAddingName] = useState<string | null>(null)
  const createEntity = useStoryStore((s) => s.createEntity)
  const addToast = useUiStore((s) => s.addToast)

  const handleAddEntity = async (char: UnknownCharacter) => {
    setAddingName(char.name)
    try {
      await createEntity(storyId, {
        entity_type: char.entity_type as 'character' | 'location' | 'prop',
        name: char.name,
        description: char.description || `A character in the story`,
        base_prompt: char.base_prompt || char.name,
      })
      setAddedNames((prev) => new Set(prev).add(char.name))
      addToast(`Added ${char.name} to World Bible`, 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to add entity', 'error')
    } finally {
      setAddingName(null)
    }
  }

  if (warnings.length === 0 && unknownCharacters.length === 0) return null

  return (
    <div className={styles.warnings}>
      {warnings.map((w, i) => (
        <div key={i} className={styles.item}>
          <span className={styles.text}>{w}</span>
        </div>
      ))}
      {unknownCharacters.map((char) => (
        <div key={char.name} className={styles.item}>
          <span className={styles.text}>Unknown character: {char.name}</span>
          <div className={styles.actions}>
            {addedNames.has(char.name) ? (
              <button className={`${styles.addBtn} ${styles.resolved}`} disabled>Added</button>
            ) : (
              <button
                className={styles.addBtn}
                onClick={() => handleAddEntity(char)}
                disabled={addingName === char.name}
              >
                {addingName === char.name ? 'Adding...' : `Add ${char.name}`}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
