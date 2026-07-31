import React, { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { COLORS } from './common/types'

const API = 'https://legislation.scriptkitty.yachts'

interface GraphNode {
  id: string
  label: string
  short_label: string
  group: string
  url: string | null
}

interface GraphEdge {
  source: string
  target: string
  label: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: { type: string; node_count: number; edge_count: number }
}

const GROUP_COLORS: Record<string, string> = {
  section: '#279e88',
  ruling: '#e67e22',
  case: '#3498db',
  definition: '#9b59b6',
  commentary: '#7f8c8d',
}

interface Props {
  type: 'section' | 'ruling' | 'case'
  act?: string
  section?: string
  citation?: string
  label: string
  onClose: () => void
}

export default function GraphModal({ type, act, section, citation, label, onClose }: Props) {
  const [data, setData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const fgRef = useRef<any>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    let url = `${API}/api/graph/data?type=${type}`
    if (type === 'section' && act && section) {
      url += `&act=${encodeURIComponent(act)}&section=${encodeURIComponent(section)}`
    } else if (citation) {
      url += `&citation=${encodeURIComponent(citation)}`
    }
    fetch(url)
      .then(r => r.json())
      .then(d => {
        if (d.error) { setError(d.error); setLoading(false); return }
        setData(d)
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [type, act, section, citation])

  const handleNodeClick = useCallback((node: GraphNode) => {
    if (node.url) {
      window.location.href = node.url
    }
  }, [])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 10000,
      background: 'rgba(0,0,0,0.7)', display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        width: '90vw', height: '85vh', maxWidth: 1200,
        background: COLORS?.surface || '#1a1a2e', borderRadius: 12,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        border: '1px solid ' + (COLORS?.border || '#333'),
      }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '12px 20px', borderBottom: '1px solid ' + (COLORS?.border || '#333'),
        }}>
          <div>
            <span style={{ fontSize: 14, color: COLORS?.heading || '#fff', fontWeight: 600 }}>
              Knowledge Graph: {label}
            </span>
            {data && (
              <span style={{ fontSize: 11, color: COLORS?.textMuted || '#888', marginLeft: 12 }}>
                {data.meta.node_count} nodes · {data.meta.edge_count} edges
              </span>
            )}
            {hoveredNode && (
              <span style={{ fontSize: 11, color: GROUP_COLORS[hoveredNode.group] || '#888', marginLeft: 12 }}>
                {hoveredNode.label}
              </span>
            )}
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: COLORS?.textMuted || '#888',
            cursor: 'pointer', fontSize: 20, lineHeight: 1, padding: '4px 8px',
          }}>✕</button>
        </div>

        {/* Legend */}
        <div style={{
          display: 'flex', gap: 16, padding: '6px 20px',
          borderBottom: '1px solid ' + (COLORS?.border || '#333'),
          fontSize: 11, color: COLORS?.textMuted || '#888',
        }}>
          {Object.entries(GROUP_COLORS).map(([g, c]) => (
            <span key={g} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
              {g}
            </span>
          ))}
          <span style={{ marginLeft: 'auto' }}>
            Click a node to navigate · Drag to move · Scroll to zoom
          </span>
        </div>

        {/* Graph */}
        <div style={{ flex: 1, position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              color: COLORS?.textMuted || '#888', fontSize: 13,
            }}>Loading graph...</div>
          )}
          {error && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              color: '#e74c3c', fontSize: 13,
            }}>Error: {error}</div>
          )}
          {data && !loading && (
            <ForceGraph2D
              ref={fgRef}
              graphData={{ nodes: data.nodes, links: data.edges }}
              nodeId="id"
              nodeLabel={n => (n as GraphNode).label}
              nodeColor={n => GROUP_COLORS[(n as GraphNode).group] || '#888'}
              nodeVal={n => (n as GraphNode).group === 'section' ? 3 : 2}
              linkLabel={e => (e as any).label}
              linkColor={() => 'rgba(255,255,255,0.15)'}
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={0.005}
              linkDirectionalArrowLength={4}
              onNodeClick={handleNodeClick}
              onNodeHover={n => setHoveredNode(n as GraphNode | null)}
              width={undefined}
              height={undefined}
              backgroundColor={COLORS?.surface || '#1a1a2e'}
              d3VelocityDecay={0.3}
              cooldownTicks={100}
              enableNodeDrag={true}
              enableZoomInteraction={true}
              minZoom={0.5}
              maxZoom={8}
            />
          )}
        </div>
      </div>
    </div>
  )
}