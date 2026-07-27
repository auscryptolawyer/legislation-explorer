import React, { useState, useEffect } from 'react'
import { api } from '../api'
import { COLORS } from './common/types'
import { shortActName } from '../utils/display'

interface RelatedSection {
  id: string
  act: string
  title: string
}

interface DefinedTerm {
  term: string
  section: string
  anchor: string
  title: string
}

interface RelatedRuling {
  citation: string
  title: string
  citation_display?: string
  full_title?: string
}

interface SmartLinkPanelProps {
  act: string
  section: string
  onNavigate?: (act: string, section: string, anchor?: string) => void
  onNavigateRuling?: (citation: string) => void
  rulingsForSection?: RelatedRuling[]
}

const SmartLinkPanel: React.FC<SmartLinkPanelProps> = ({ act, section, onNavigate, onNavigateRuling, rulingsForSection }) => {
  const [relatedSections, setRelatedSections] = useState<RelatedSection[]>([])
  const [definedTerms, setDefinedTerms] = useState<DefinedTerm[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [refs, defTerms] = await Promise.all([
          api.sectionRefs(act, section),
          api.sectionDefinedTerms(act, section).catch(() => ({ terms: [] })),
        ])
        setRelatedSections(refs.sections || [])
        // Merge definitions from both sources
        const refDefs: DefinedTerm[] = (refs.definitions || []).map((d: any) => ({
          term: d.term || d.id || '',
          section: d.section || '',
          anchor: d.anchor || '',
          title: d.title || `s ${d.section}`,
        }))
        const bodyDefs: DefinedTerm[] = (defTerms.terms || []).map((d: any) => ({
          term: d.term,
          section: d.section,
          anchor: d.anchor,
          title: `s ${d.section}`,
        }))
        // Deduplicate by term
        const seen = new Set<string>()
        const merged = [...refDefs, ...bodyDefs].filter(d => {
          if (seen.has(d.term.toLowerCase())) return false
          seen.add(d.term.toLowerCase())
          return true
        })
        setDefinedTerms(merged)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [act, section])

  const handleSectionClick = (link: RelatedSection) => {
    if (onNavigate) {
      onNavigate(link.act, link.id)
    }
  }

  const handleDefinitionClick = (def: DefinedTerm) => {
    if (onNavigate) {
      onNavigate(act, def.section, def.anchor)
    }
  }

  const handleRulingClick = (r: RelatedRuling) => {
    if (onNavigateRuling) {
      onNavigateRuling(r.citation)
    }
  }

  const panelStyle: React.CSSProperties = {
    background: COLORS.surface,
    borderRadius: 8,
    padding: 12,
    border: `1px solid ${COLORS.border}`,
    boxShadow: `0 2px 4px rgba(0,0,0,0.2)`,
  }

  const groupTitleStyle: React.CSSProperties = {
    color: COLORS.heading,
    fontSize: 13,
    fontWeight: 600,
    margin: '12px 0 8px',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  }

  const itemBaseStyle: React.CSSProperties = {
    marginBottom: 6,
    padding: '8px 10px',
    borderRadius: 4,
    fontSize: 13,
    display: 'flex',
    alignItems: 'center',
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
  }

  const clickableItemStyle: React.CSSProperties = {
    ...itemBaseStyle,
    cursor: 'pointer',
    color: COLORS.accent,
  }

  const rulings = rulingsForSection || []
  const hasContent = relatedSections.length > 0 || definedTerms.length > 0 || rulings.length > 0

  if (loading) {
    return <div style={{ padding: '12px 0', color: COLORS.textMuted, fontSize: 13 }}>Loading related information...</div>
  }

  if (error) {
    return <div style={{ padding: '12px 0', color: '#ef4444', fontSize: 13 }}>Error: {error}</div>
  }

  if (!hasContent) {
    return null
  }

  return (
    <div style={panelStyle}>
      <h3 style={{ color: COLORS.heading, fontSize: 14, fontWeight: 600, margin: '0 0 4px' }}>Related</h3>

      {relatedSections.length > 0 && (
        <>
          <h4 style={groupTitleStyle}>Sections</h4>
          {relatedSections.map((link) => (
            <div
              key={link.act + link.id}
              style={clickableItemStyle}
              onClick={() => handleSectionClick(link)}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
            >
              {shortActName(link.act)} s{link.id}{link.title ? ` — ${link.title}` : ''}
            </div>
          ))}
        </>
      )}

      {rulings.length > 0 && (
        <>
          <h4 style={groupTitleStyle}>Rulings</h4>
          {rulings.map((r) => (
            <div
              key={r.citation}
              style={clickableItemStyle}
              onClick={() => handleRulingClick(r)}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
            >
              {r.title || r.citation_display || r.citation}
            </div>
          ))}
        </>
      )}

      {definedTerms.length > 0 && (
        <>
          <h4 style={groupTitleStyle}>Defined Terms</h4>
          {definedTerms.map((def) => (
            <div
              key={def.term}
              style={clickableItemStyle}
              onClick={() => handleDefinitionClick(def)}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
            >
              <span style={{ fontWeight: 500, color: COLORS.text }}>{def.term}</span>
              {' — '}
              <span style={{ color: COLORS.textMuted }}>defined in {def.title || `s ${def.section}`}</span>
            </div>
          ))}
        </>
      )}

      {/* Cases — placeholder for future */}
      <h4 style={{ ...groupTitleStyle, opacity: 0.4 }}>Cases</h4>
      <div style={{ ...itemBaseStyle, opacity: 0.4, cursor: 'default', color: COLORS.textMuted, fontStyle: 'italic' }}>
        Coming soon
      </div>

      {/* Commentary — placeholder for future */}
      <h4 style={{ ...groupTitleStyle, opacity: 0.4 }}>Commentary</h4>
      <div style={{ ...itemBaseStyle, opacity: 0.4, cursor: 'default', color: COLORS.textMuted, fontStyle: 'italic' }}>
        Coming soon
      </div>
    </div>
  )
}

export default SmartLinkPanel