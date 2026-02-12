import styles from '../../styles/components/Spinner.module.css'

export default function Spinner({ size = 14 }: { size?: number }) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size }}
    />
  )
}
