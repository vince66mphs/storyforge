import { useEffect } from 'react'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/LightboxModal.module.css'

export default function LightboxModal() {
  const src = useUiStore((s) => s.lightboxSrc)
  const caption = useUiStore((s) => s.lightboxCaption)
  const close = useUiStore((s) => s.closeLightbox)

  useEffect(() => {
    if (!src) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [src, close])

  if (!src) return null

  return (
    <div className={styles.overlay} onClick={close}>
      <button className={styles.close} onClick={close}>&times;</button>
      <img className={styles.img} src={src} alt={caption ?? 'Image'} onClick={(e) => e.stopPropagation()} />
      {caption && <div className={styles.caption}>{caption}</div>}
    </div>
  )
}
