import type { Beat } from '../../types/api'
import styles from '../../styles/components/SceneBeat.module.css'

interface Props {
  beat: Beat
}

export default function SceneBeat({ beat }: Props) {
  return (
    <details className={styles.beat}>
      <summary>Scene Beat</summary>
      <div className={styles.content}>
        {beat.setting && (
          <div><strong>Setting:</strong> {beat.setting}</div>
        )}
        {beat.characters && beat.characters.length > 0 && (
          <div>
            <strong>Characters:</strong>
            <ul>
              {beat.characters.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}
        {beat.conflict && (
          <div><strong>Conflict:</strong> {beat.conflict}</div>
        )}
        {beat.tone && (
          <div><strong>Tone:</strong> {beat.tone}</div>
        )}
        {beat.foreshadowing && (
          <div><strong>Foreshadowing:</strong> {beat.foreshadowing}</div>
        )}
      </div>
    </details>
  )
}
