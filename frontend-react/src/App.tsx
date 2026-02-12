import { useUiStore } from './store/uiStore'
import LobbyView from './components/lobby/LobbyView'
import WritingView from './components/writing/WritingView'
import ToastContainer from './components/shared/ToastContainer'

export default function App() {
  const view = useUiStore((s) => s.view)

  return (
    <>
      {view === 'lobby' ? <LobbyView /> : <WritingView />}
      <ToastContainer />
    </>
  )
}
