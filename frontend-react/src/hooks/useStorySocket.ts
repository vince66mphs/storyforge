import { useRef, useEffect, useCallback } from 'react'
import type { NodeResponse } from '../types/api'
import type { ServerMessage, GenerateMessage, BranchMessage } from '../types/websocket'

interface Options {
  onToken: (text: string) => void
  onPhase: (phase: 'planning' | 'writing') => void
  onComplete: (node: NodeResponse) => void
  onIllustration: (nodeId: string, path: string) => void
  onError: (message: string) => void
  onGenerating: (generating: boolean) => void
}

interface SocketHandle {
  generate: (storyId: string, prompt: string, parentNodeId?: string) => void
  branch: (storyId: string, nodeId: string, prompt: string) => void
  connected: boolean
}

export default function useStorySocket(opts: Options): SocketHandle {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalClose = useRef(false)
  const connectedRef = useRef(false)
  const optsRef = useRef(opts)
  optsRef.current = opts

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/ws/generate`
    intentionalClose.current = false
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      connectedRef.current = true
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
    }

    ws.onmessage = (event) => {
      let msg: ServerMessage
      try {
        msg = JSON.parse(event.data)
      } catch {
        return
      }

      switch (msg.type) {
        case 'token':
          optsRef.current.onToken(msg.content)
          break
        case 'phase':
          optsRef.current.onPhase(msg.phase)
          break
        case 'complete':
          optsRef.current.onComplete(msg.node)
          break
        case 'illustration':
          optsRef.current.onIllustration(msg.node_id, msg.path)
          break
        case 'error':
          optsRef.current.onError(msg.message)
          break
      }
    }

    ws.onclose = () => {
      connectedRef.current = false
      if (!intentionalClose.current && !reconnectTimer.current) {
        reconnectTimer.current = setTimeout(() => {
          reconnectTimer.current = null
          connect()
        }, 3000)
      }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      intentionalClose.current = true
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  const send = useCallback((msg: GenerateMessage | BranchMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
      return true
    }
    return false
  }, [])

  const generate = useCallback((storyId: string, prompt: string, parentNodeId?: string) => {
    optsRef.current.onGenerating(true)
    optsRef.current.onPhase('planning')
    const msg: GenerateMessage = {
      action: 'generate',
      story_id: storyId,
      prompt,
      ...(parentNodeId ? { parent_node_id: parentNodeId } : {}),
    }
    send(msg)
  }, [send])

  const branch = useCallback((storyId: string, nodeId: string, prompt: string) => {
    optsRef.current.onGenerating(true)
    optsRef.current.onPhase('planning')
    const msg: BranchMessage = { action: 'branch', story_id: storyId, node_id: nodeId, prompt }
    send(msg)
  }, [send])

  return {
    generate,
    branch,
    get connected() { return connectedRef.current },
  }
}
