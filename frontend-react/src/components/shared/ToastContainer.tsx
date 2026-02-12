import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/Toast.module.css'

export default function ToastContainer() {
  const toasts = useUiStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <div className={styles.container}>
      {toasts.map((toast) => (
        <div key={toast.id} className={`${styles.toast} ${styles[toast.type] ?? ''}`}>
          {toast.message}
        </div>
      ))}
    </div>
  )
}
