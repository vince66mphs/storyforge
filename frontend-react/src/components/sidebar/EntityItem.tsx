import type { EntityResponse } from '../../types/api'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/EntityItem.module.css'

const ENTITY_ICONS: Record<string, string> = {
  character: '\u{1F464}',
  location: '\u{1F3D4}',
  prop: '\u{1F4E6}',
}

interface Props {
  entity: EntityResponse
}

export default function EntityItem({ entity }: Props) {
  const openEntityDetail = useUiStore((s) => s.openEntityDetail)
  const openLightbox = useUiStore((s) => s.openLightbox)
  const openImageGrid = useUiStore((s) => s.openImageGrid)

  const handleThumbClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (entity.reference_image_path) {
      openLightbox(`/static/images/${entity.reference_image_path}`, entity.name)
    } else {
      openImageGrid(entity.id)
    }
  }

  return (
    <div className={styles.item} onClick={() => openEntityDetail(entity)}>
      {entity.reference_image_path ? (
        <img
          className={styles.thumb}
          src={`/static/images/${entity.reference_image_path}`}
          alt={entity.name}
          onClick={handleThumbClick}
        />
      ) : (
        <div className={styles.placeholder} onClick={handleThumbClick}>
          {ENTITY_ICONS[entity.entity_type] ?? '\u{2753}'}
        </div>
      )}
      <div className={styles.info}>
        <div className={styles.name}>{entity.name}</div>
        <div className={styles.type}>{entity.entity_type}</div>
      </div>
    </div>
  )
}
