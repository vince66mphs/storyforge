import { useState } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/AddEntityForm.module.css'

interface Props {
  onDone: () => void
}

export default function AddEntityForm({ onDone }: Props) {
  const [name, setName] = useState('')
  const [entityType, setEntityType] = useState<'character' | 'location' | 'prop'>('character')
  const [description, setDescription] = useState('')
  const [basePrompt, setBasePrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const currentStory = useStoryStore((s) => s.currentStory)
  const createEntity = useStoryStore((s) => s.createEntity)
  const addToast = useUiStore((s) => s.addToast)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentStory || !name.trim() || submitting) return

    setSubmitting(true)
    try {
      await createEntity(currentStory.id, {
        entity_type: entityType,
        name: name.trim(),
        description: description.trim() || name.trim(),
        base_prompt: basePrompt.trim() || name.trim(),
      })
      addToast(`Added ${name}`, 'success')
      onDone()
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to add entity', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Type</label>
        <select value={entityType} onChange={(e) => setEntityType(e.target.value as typeof entityType)}>
          <option value="character">Character</option>
          <option value="location">Location</option>
          <option value="prop">Prop</option>
        </select>
      </div>
      <div className="form-group">
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Entity name" required />
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description..." rows={2} />
      </div>
      <div className="form-group">
        <label>Image Prompt</label>
        <input value={basePrompt} onChange={(e) => setBasePrompt(e.target.value)} placeholder="Visual description for image generation" />
      </div>
      <div className={styles.actions}>
        <button type="button" className="btn btn-ghost btn-small" onClick={onDone}>Cancel</button>
        <button type="submit" className="btn btn-primary btn-small" disabled={!name.trim() || submitting}>
          {submitting ? 'Adding...' : 'Add'}
        </button>
      </div>
    </form>
  )
}
