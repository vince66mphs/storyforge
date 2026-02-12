import { useState, useRef, useCallback } from 'react'

export interface SSEItem {
  index: number
  filename: string
  seed: number
}

interface SSEState {
  items: SSEItem[]
  loading: boolean
  done: boolean
  start: (url: string) => void
  stop: () => void
}

export default function useSSE(): SSEState {
  const [items, setItems] = useState<SSEItem[]>([])
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
  }, [])

  const start = useCallback((url: string) => {
    stop()
    setItems([])
    setDone(false)
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    fetch(url, { method: 'POST', signal: controller.signal })
      .then(async (res) => {
        if (!res.ok || !res.body) {
          setLoading(false)
          setDone(true)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done: readerDone, value } = await reader.read()
          if (readerDone) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6)) as SSEItem
                setItems((prev) => [...prev, data])
              } catch {
                // skip malformed lines
              }
            }
          }
        }

        setLoading(false)
        setDone(true)
      })
      .catch(() => {
        setLoading(false)
        setDone(true)
      })
  }, [stop])

  return { items, loading, done, start, stop }
}
