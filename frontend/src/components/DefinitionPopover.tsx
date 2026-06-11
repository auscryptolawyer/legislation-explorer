import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { COLORS } from './common/types'

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (React.isValidElement(node)) {
    return extractText(node.props.children)
  }
  return ''
}

type DefinitionData = {
  term: string
  act: string
  section: string
  anchor: string
  text: string
  path: string
}

export default function DefinitionPopover({
  act,
  children,
  href,
  onNavigate,
}: {
  act: string
  children: React.ReactNode
  href?: string
  onNavigate: (section: string, anchor?: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<DefinitionData | null>(null)
  const [error, setError] = useState('')
  const containerRef = useRef<HTMLSpanElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)

  const termText = extractText(children).trim()

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const handleOpen = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (open) {
      setOpen(false)
      return
    }
    setOpen(true)
    if (data) return
    setLoading(true)
    setError('')
    try {
      const res = await api.definitionText(act, termText)
      setData(res)
    } catch (err: any) {
      setError(err.message || 'Failed to load definition')
    } finally {
      setLoading(false)
    }
  }

  const handleNavigate = () => {
    if (!data) return
    setOpen(false)
    onNavigate(data.section, data.anchor)
  }

  return (
    <span ref={containerRef} style={{ position: 'relative', display: 'inline' }}>
      <span
        onClick={handleOpen}
        style={{
          color: COLORS.accent,
          cursor: 'pointer',
          textDecoration: 'none',
          borderBottom: `1px dashed ${COLORS.accentHover}`,
        }}
      >
        {children}
      </span>
      {open && (
        <div
          ref={popoverRef}
          style={{
            position: 'absolute',
            zIndex: 1000,
            top: 'calc(100% + 8px)',
            left: 0,
            maxWidth: 400,
            minWidth: 280,
            background: COLORS.surface,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 6,
            padding: '12px 16px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
            fontFamily: "'Lora', serif",
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: -6,
              left: 16,
              width: 10,
              height: 10,
              background: COLORS.surface,
              borderLeft: `1px solid ${COLORS.border}`,
              borderTop: `1px solid ${COLORS.border}`,
              transform: 'rotate(45deg)',
            }}
          />
          {loading && (
            <div style={{ color: COLORS.textMuted, fontSize: 13 }}>Loading definition...</div>
          )}
          {error && (
            <div style={{ color: '#ef4444', fontSize: 13 }}>{error}</div>
          )}
          {data && (
            <div>
              <div
                style={{
                  color: COLORS.heading,
                  fontWeight: 600,
                  fontSize: 14,
                  marginBottom: 8,
                  fontFamily: "'Montserrat', sans-serif",
                }}
              >
                {data.term}
              </div>
              <div
                style={{
                  color: COLORS.text,
                  fontSize: 13,
                  lineHeight: 1.6,
                  marginBottom: 10,
                }}
              >
                {data.text}
              </div>
              <div
                onClick={handleNavigate}
                style={{
                  color: COLORS.accent,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: "'Montserrat', sans-serif",
                }}
              >
                Go to definition →
              </div>
            </div>
          )}
        </div>
      )}
    </span>
  )
}
