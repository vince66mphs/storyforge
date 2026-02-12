import EntityPanel from '../sidebar/EntityPanel'
import NarrativeDAG from '../sidebar/NarrativeDAG'
import styles from '../../styles/components/Sidebar.module.css'

export default function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <EntityPanel />
      <div className={styles.section}>
        <h3>Story Tree</h3>
        <NarrativeDAG />
      </div>
    </aside>
  )
}
