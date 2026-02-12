import { useState, useEffect, useRef } from 'react'
import { useUiStore } from '../../store/uiStore'
import { useStoryStore } from '../../store/storyStore'
import { describeEntityFromImage, uploadEntityImage } from '../../api/entities'
import styles from '../../styles/components/EntityDetailModal.module.css'

const ENTITY_ICONS: Record<string, string> = {
  character: '\u{1F464}',
  location: '\u{1F3D4}',
  prop: '\u{1F4E6}',
}

export default function EntityDetailModal() {
  const entity = useUiStore((s) => s.entityDetailEntity)
  const close = useUiStore((s) => s.closeEntityDetail)
  const openImageGrid = useUiStore((s) => s.openImageGrid)
  const openLightbox = useUiStore((s) => s.openLightbox)
  const addToast = useUiStore((s) => s.addToast)
  const updateEntityAction = useStoryStore((s) => s.updateEntity)
  const replaceEntity = useStoryStore((s) => s.replaceEntity)

  const [description, setDescription] = useState('')
  const [basePrompt, setBasePrompt] = useState('')
  const [saving, setSaving] = useState(false)
  const [describing, setDescribing] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (entity) {
      setDescription(entity.description)
      setBasePrompt(entity.base_prompt)
    }
  }, [entity])

  useEffect(() => {
    if (!entity) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [entity, close])

  if (!entity) return null

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateEntityAction(entity.id, { description, base_prompt: basePrompt })
      // Update parent's view of entity
      useUiStore.getState().openEntityDetail(updated)
      addToast('Entity updated', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const updated = await uploadEntityImage(entity.id, file)
      replaceEntity(updated)
      useUiStore.getState().openEntityDetail(updated)
      addToast('Image uploaded', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Upload failed', 'error')
    }
  }

  const handleDescribe = async () => {
    setDescribing(true)
    try {
      const updated = await describeEntityFromImage(entity.id)
      replaceEntity(updated)
      useUiStore.getState().openEntityDetail(updated)
      setDescription(updated.description)
      setBasePrompt(updated.base_prompt)
      addToast('Description generated from image', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Describe failed', 'error')
    } finally {
      setDescribing(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={close}>
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div>
            <h3>{ENTITY_ICONS[entity.entity_type] ?? ''} {entity.name}</h3>
            <span className={styles.type}>{entity.entity_type}</span>
          </div>
          <button className={styles.closeBtn} onClick={close}>&times;</button>
        </div>

        <div className={styles.imageSection}>
          {entity.reference_image_path ? (
            <img
              className={styles.image}
              src={`/static/images/${entity.reference_image_path}`}
              alt={entity.name}
              onClick={() => openLightbox(`/static/images/${entity.reference_image_path!}`, entity.name)}
            />
          ) : (
            <div className={styles.imageEmpty}>No reference image</div>
          )}
          <div className={styles.imageActions}>
            <button className="btn btn-small btn-secondary" onClick={() => openImageGrid(entity.id)}>
              Generate Image
            </button>
            <button className="btn btn-small" onClick={() => fileRef.current?.click()}>
              Upload Image
            </button>
            {entity.reference_image_path && (
              <button
                className="btn btn-small"
                onClick={handleDescribe}
                disabled={describing}
              >
                {describing ? 'Describing...' : 'Describe from Image'}
              </button>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleUpload} />
        </div>

        <div className={styles.fields}>
          <div className="form-group">
            <label>Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </div>
          <div className="form-group">
            <label>Image Prompt</label>
            <textarea value={basePrompt} onChange={(e) => setBasePrompt(e.target.value)} rows={3} />
          </div>
          <div className={styles.saveRow}>
            <span className={styles.version}>v{entity.version}</span>
            <button
              className="btn btn-primary btn-small"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
