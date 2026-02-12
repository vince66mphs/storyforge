import { useUiStore } from '../../store/uiStore'
import Spinner from '../shared/Spinner'
import styles from '../../styles/components/GeneratingIndicator.module.css'

const STEPS = ['planning', 'writing'] as const

export default function GeneratingIndicator() {
  const phase = useUiStore((s) => s.generatingPhase)

  return (
    <div className={styles.indicator}>
      <Spinner />
      <div className={styles.steps}>
        {STEPS.map((step, i) => {
          const stepIdx = phase ? STEPS.indexOf(phase) : -1
          const currentIdx = STEPS.indexOf(step)
          let cls = styles.pending
          if (currentIdx < stepIdx) cls = styles.done
          else if (currentIdx === stepIdx) cls = styles.active

          return (
            <span key={step}>
              {i > 0 && <span className={styles.arrow}>&rsaquo;</span>}
              <span className={`${styles.step} ${cls}`}>
                {step.charAt(0).toUpperCase() + step.slice(1)}
              </span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
