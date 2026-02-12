import { useState } from 'react'
import type { NodeResponse } from '../../types/api'
import { illustrateNode } from '../../api/nodes'
import { useUiStore } from '../../store/uiStore'
import { useStoryStore } from '../../store/storyStore'
import SceneBeat from './SceneBeat'
import SceneWarnings from './SceneWarnings'
import styles from '../../styles/components/Scenes.module.css'

interface Props {
  node: NodeResponse
}

export default function Scene({ node }: Props) {
  const [illustrating, setIllustrating] = useState(false)
  const addToast = useUiStore((s) => s.addToast)
  const openLightbox = useUiStore((s) => s.openLightbox)
  const updateNodeIllustration = useStoryStore((s) => s.updateNodeIllustration)

  const time = new Date(node.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  const handleIllustrate = async () => {
    setIllustrating(true)
    try {
      const updated = await illustrateNode(node.id)
      if (updated.illustration_path) {
        updateNodeIllustration(node.id, updated.illustration_path)
      }
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Illustration failed', 'error')
    } finally {
      setIllustrating(false)
    }
  }

  return (
    <div className={styles.scene}>
      <div className={styles.meta}>
        {node.node_type === 'root' ? 'Opening' : 'Scene'} · {time}
      </div>

      {node.illustration_path && (
        <div className={styles.illustration}>
          <img
            src={`/static/images/${node.illustration_path}`}
            alt="Scene illustration"
            onClick={() => openLightbox(`/static/images/${node.illustration_path!}`)}
          />
        </div>
      )}

      {illustrating && (
        <div className={styles.illustration} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 10, padding: 32, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius)',
          color: 'var(--text-dim)', fontSize: 13,
        }}>
          <span className="spinner" style={{ width: 14, height: 14, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block' }} />
          Generating illustration...
        </div>
      )}

      <div className={styles.content}>{node.content}</div>

      <div className={styles.actions}>
        {!node.illustration_path && !illustrating && (
          <button
            className={`btn btn-ghost btn-small ${styles.illustrateBtn}`}
            onClick={handleIllustrate}
          >
            Illustrate
          </button>
        )}
      </div>

      {node.beat && <SceneBeat beat={node.beat} />}
      {(node.continuity_warnings.length > 0 || node.unknown_characters.length > 0) && (
        <SceneWarnings
          warnings={node.continuity_warnings}
          unknownCharacters={node.unknown_characters}
          storyId={node.story_id}
        />
      )}
    </div>
  )
}
