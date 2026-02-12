import { useStoryStore } from '../../store/storyStore'
import StoryCard from './StoryCard'
import styles from '../../styles/components/StoryList.module.css'

export default function StoryList() {
  const stories = useStoryStore((s) => s.stories)

  return (
    <section className={styles.section}>
      <h2>Your Stories</h2>
      {stories.length === 0 ? (
        <p className={styles.empty}>No stories yet. Create one to get started!</p>
      ) : (
        <div className={styles.list}>
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      )}
    </section>
  )
}
