import { useEffect } from 'react'
import { useStoryStore } from '../../store/storyStore'
import CreateStoryForm from './CreateStoryForm'
import StoryList from './StoryList'
import styles from '../../styles/components/Lobby.module.css'

export default function LobbyView() {
  const fetchStories = useStoryStore((s) => s.fetchStories)

  useEffect(() => {
    fetchStories()
  }, [fetchStories])

  return (
    <div className={styles.lobby}>
      <header className={styles.header}>
        <h1>StoryForge <span className={styles.version}>2.0</span></h1>
        <p className={styles.subtitle}>AI-powered interactive storytelling</p>
      </header>
      <div className={styles.content}>
        <CreateStoryForm />
        <StoryList />
      </div>
    </div>
  )
}
