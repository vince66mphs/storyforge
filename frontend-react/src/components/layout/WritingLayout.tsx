import Sidebar from './Sidebar'
import ScenesContainer from '../writing/ScenesContainer'
import StreamingScene from '../writing/StreamingScene'
import GeneratingIndicator from '../writing/GeneratingIndicator'
import PromptArea from '../writing/PromptArea'
import SettingsPanel from '../writing/SettingsPanel'
import { useUiStore } from '../../store/uiStore'
import EntityDetailModal from '../modals/EntityDetailModal'
import ImageGridModal from '../modals/ImageGridModal'
import LightboxModal from '../modals/LightboxModal'
import ContinuityCheckModal from '../modals/ContinuityCheckModal'
import styles from '../../styles/components/WritingLayout.module.css'

interface Props {
  socket: {
    generate: (storyId: string, prompt: string, parentNodeId?: string) => void
    branch: (storyId: string, nodeId: string, prompt: string) => void
  }
}

export default function WritingLayout({ socket }: Props) {
  const showSettingsPanel = useUiStore((s) => s.showSettingsPanel)
  const isGenerating = useUiStore((s) => s.isGenerating)

  return (
    <>
      <div className={styles.layout}>
        <Sidebar />
        <main className={styles.main}>
          <ScenesContainer />
          {isGenerating && <StreamingScene />}
          {isGenerating && <GeneratingIndicator />}
          <PromptArea socket={socket} />
          {showSettingsPanel && <SettingsPanel />}
        </main>
      </div>
      <EntityDetailModal />
      <ImageGridModal />
      <LightboxModal />
      <ContinuityCheckModal />
    </>
  )
}
