import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Controls,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useStoryStore } from '../../store/storyStore'
import StoryNode from './StoryNode'
import styles from '../../styles/components/NarrativeDAG.module.css'

const nodeTypes = { storyNode: StoryNode }

function buildFlowLayout(nodes: ReturnType<typeof useStoryStore.getState>['allNodes'], activeNodeId: string | null) {
  // Build children map
  const childrenMap: Record<string, string[]> = {}
  const nodeMap: Record<string, (typeof nodes)[number]> = {}
  let rootId: string | null = null

  for (const n of nodes) {
    nodeMap[n.id] = n
    if (!n.parent_id) {
      rootId = n.id
    } else {
      if (!childrenMap[n.parent_id]) childrenMap[n.parent_id] = []
      childrenMap[n.parent_id]!.push(n.id)
    }
  }

  if (!rootId) return { nodes: [], edges: [] }

  const flowNodes: Node[] = []
  const flowEdges: Edge[] = []

  // BFS with position calculation
  const queue: { id: string; depth: number; x: number }[] = [{ id: rootId, depth: 0, x: 0 }]
  const visited = new Set<string>()

  // Calculate horizontal positions using a simple algorithm
  const depthCounters: Record<number, number> = {}

  while (queue.length > 0) {
    const item = queue.shift()!
    if (visited.has(item.id)) continue
    visited.add(item.id)

    const node = nodeMap[item.id]
    if (!node) continue

    const depth = item.depth
    if (depthCounters[depth] === undefined) depthCounters[depth] = 0
    const xPos = depthCounters[depth]! * 160
    depthCounters[depth] = depthCounters[depth]! + 1

    const preview = node.content.slice(0, 30).replace(/\n/g, ' ')
    const isActive = node.id === activeNodeId

    flowNodes.push({
      id: node.id,
      type: 'storyNode',
      position: { x: xPos, y: depth * 80 },
      data: { label: preview, isActive, hasIllustration: !!node.illustration_path },
    })

    if (node.parent_id) {
      flowEdges.push({
        id: `${node.parent_id}-${node.id}`,
        source: node.parent_id,
        target: node.id,
        style: { stroke: 'var(--text-dim)', strokeWidth: 1.5 },
      })
    }

    const children = childrenMap[node.id] ?? []
    for (const childId of children) {
      queue.push({ id: childId, depth: depth + 1, x: 0 })
    }
  }

  return { nodes: flowNodes, edges: flowEdges }
}

export default function NarrativeDAG() {
  const allNodes = useStoryStore((s) => s.allNodes)
  const currentLeafId = useStoryStore((s) => s.currentLeafId)
  const navigateToNode = useStoryStore((s) => s.navigateToNode)

  const { nodes, edges } = useMemo(
    () => buildFlowLayout(allNodes, currentLeafId),
    [allNodes, currentLeafId],
  )

  const handleNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    navigateToNode(node.id)
  }, [navigateToNode])

  if (allNodes.length === 0) {
    return <div className={styles.empty}>No story tree yet</div>
  }

  return (
    <div className={styles.container}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  )
}
