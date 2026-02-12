import { Handle, Position, type NodeProps } from '@xyflow/react'
import styles from '../../styles/components/StoryNode.module.css'

interface StoryNodeData {
  label: string
  isActive: boolean
  hasIllustration: boolean
  [key: string]: unknown
}

export default function StoryNode({ data }: NodeProps) {
  const { label, isActive, hasIllustration } = data as StoryNodeData

  return (
    <div className={`${styles.node} ${isActive ? styles.active : ''}`}>
      <Handle type="target" position={Position.Top} className={styles.handle} />
      <div className={styles.label}>
        {hasIllustration && <span className={styles.badge} title="Has illustration" />}
        {label}
      </div>
      <Handle type="source" position={Position.Bottom} className={styles.handle} />
    </div>
  )
}
