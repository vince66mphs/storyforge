import styles from '../../styles/components/ContentModeToggle.module.css'

interface Props {
  value: 'unrestricted' | 'safe'
  onChange: (mode: 'unrestricted' | 'safe') => void
}

export default function ContentModeToggle({ value, onChange }: Props) {
  return (
    <div className={styles.toggleGroup}>
      <button
        type="button"
        className={`${styles.toggleBtn} ${value === 'unrestricted' ? styles.active : ''}`}
        onClick={() => onChange('unrestricted')}
      >
        Unrestricted
      </button>
      <button
        type="button"
        className={`${styles.toggleBtn} ${value === 'safe' ? styles.active : ''}`}
        onClick={() => onChange('safe')}
      >
        Safe
      </button>
    </div>
  )
}
