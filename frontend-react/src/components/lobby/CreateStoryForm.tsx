import { useState } from 'react'
import { useStoryStore } from '../../store/storyStore'
import { useUiStore } from '../../store/uiStore'
import ContentModeToggle from '../shared/ContentModeToggle'
import styles from '../../styles/components/CreateStoryForm.module.css'

export default function CreateStoryForm() {
  const [title, setTitle] = useState('')
  const [genre, setGenre] = useState('')
  const [contentMode, setContentMode] = useState<'unrestricted' | 'safe'>('unrestricted')
  const [openingPrompt, setOpeningPrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const createStory = useStoryStore((s) => s.createStory)
  const openStory = useStoryStore((s) => s.openStory)
  const setView = useUiStore((s) => s.setView)
  const addToast = useUiStore((s) => s.addToast)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || submitting) return

    setSubmitting(true)
    try {
      const story = await createStory(title.trim(), genre.trim() || null, contentMode)
      openStory(story)
      setView('writing')
      // If there's an opening prompt, the WritingView will handle it
      if (openingPrompt.trim()) {
        // Store it in sessionStorage for WritingView to pick up
        sessionStorage.setItem('openingPrompt', openingPrompt.trim())
      }
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to create story', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.section}>
      <h2>New Story</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a story title..."
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="genre">Genre <span className="optional">(optional)</span></label>
          <input
            id="genre"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            placeholder="Fantasy, Sci-Fi, Mystery..."
          />
        </div>
        <div className="form-group">
          <label>Content Mode</label>
          <ContentModeToggle value={contentMode} onChange={setContentMode} />
        </div>
        <div className="form-group">
          <label htmlFor="opening">Opening Prompt <span className="optional">(optional)</span></label>
          <textarea
            id="opening"
            value={openingPrompt}
            onChange={(e) => setOpeningPrompt(e.target.value)}
            placeholder="Describe how you'd like the story to begin..."
            rows={3}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={!title.trim() || submitting}>
          {submitting ? 'Creating...' : 'Create Story'}
        </button>
      </form>
    </section>
  )
}
