import { useEffect, useCallback } from 'react'
import { useUiStore } from '../../store/uiStore'
import { useStoryStore } from '../../store/storyStore'
import { generateEntityImagesUrl, selectEntityImage } from '../../api/entities'
import useSSE from '../../hooks/useSSE'
import Spinner from '../shared/Spinner'
import styles from '../../styles/components/ImageGridModal.module.css'

export default function ImageGridModal() {
  const entityId = useUiStore((s) => s.imageGridEntityId)
  const close = useUiStore((s) => s.closeImageGrid)
  const addToast = useUiStore((s) => s.addToast)
  const replaceEntity = useStoryStore((s) => s.replaceEntity)
  const entities = useStoryStore((s) => s.entities)

  const { items, loading, start, stop } = useSSE()

  const entity = entities.find((e) => e.id === entityId)

  // Start generation when modal opens
  useEffect(() => {
    if (entityId) {
      start(generateEntityImagesUrl(entityId))
    }
    return () => stop()
  }, [entityId]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = useCallback(async (filename: string, seed: number) => {
    if (!entityId) return
    const rejectFilenames = items
      .filter((it) => it.filename !== filename)
      .map((it) => it.filename)

    try {
      const updated = await selectEntityImage(entityId, {
        filename,
        seed,
        reject_filenames: rejectFilenames,
      })
      replaceEntity(updated)
      close()
      addToast('Image selected', 'success')
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to select image', 'error')
    }
  }, [entityId, items, replaceEntity, close, addToast])

  useEffect(() => {
    if (!entityId) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { stop(); close() }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [entityId, close, stop])

  if (!entityId) return null

  return (
    <div className={styles.overlay} onClick={() => { stop(); close() }}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>{entity ? `Images for ${entity.name}` : 'Generating Images'}</h3>
          <button className={styles.closeBtn} onClick={() => { stop(); close() }}>&times;</button>
        </div>
        <div className={styles.grid}>
          {[0, 1, 2, 3].map((i) => {
            const item = items[i]
            return (
              <div key={i} className={styles.slot}>
                {item ? (
                  <img
                    className={styles.img}
                    src={`/static/images/${item.filename}`}
                    alt={`Option ${i + 1}`}
                    onClick={() => handleSelect(item.filename, item.seed)}
                  />
                ) : (
                  <div className={styles.placeholder}>
                    {loading && <Spinner size={20} />}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {loading && (
          <div className={styles.footer}>
            <Spinner /> Generating...
          </div>
        )}
      </div>
    </div>
  )
}
