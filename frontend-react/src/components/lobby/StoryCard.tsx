import type { StoryResponse } from '../../types/api'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import styles from '../../styles/components/StoryCard.module.css'

interface Props {
  story: StoryResponse
}

export default function StoryCard({ story }: Props) {
  const openStory = useStoryStore((s) => s.openStory)
  const deleteStoryAction = useStoryStore((s) => s.deleteStory)
  const setView = useUiStore((s) => s.setView)
  const addToast = useUiStore((s) => s.addToast)

  const handleClick = () => {
    openStory(story)
    setView('writing')
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm(`Delete "${story.title}"?`)) return
    try {
      await deleteStoryAction(story.id)
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to delete story', 'error')
    }
  }

  const date = new Date(story.created_at).toLocaleDateString()

  return (
    <div className={styles.card} onClick={handleClick}>
      <div className={styles.info}>
        <h3>{story.title}</h3>
        <div className={styles.meta}>
          {story.genre && <span>{story.genre}</span>}
          {story.genre && <span> · </span>}
          <span>{story.content_mode}</span>
          <span> · </span>
          <span>{date}</span>
        </div>
      </div>
      <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
    </div>
  )
}
