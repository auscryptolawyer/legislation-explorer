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

interface RelatedCase {
  citation: string
  title: string
  court: string
}

interface RelatedCommentaryItem {
  publication: string
  chapter_number?: string
  chapter_title?: string
  heading_title: string
  paragraph_number?: string
}

interface SmartLinkPanelProps {
  act: string
  section: string
  onNavigate?: (act: string, section: string, anchor?: string) => void
  onNavigateRuling?: (citation: string) => void
  onNavigateCase?: (citation: string) => void
  rulingsForSection?: RelatedRuling[]
  casesData?: { cases?: RelatedCase[] }
  commentaryData?: RelatedCommentaryItem[] | { commentary?: RelatedCommentaryItem[] }
}

const MAX_ITEMS = 10

// Collapsible dropdown group
function CollapsibleGroup({
  title, count, open, setOpen, children,
}: {
  title: string; count: number; open: boolean; setOpen: (v: boolean) => void; children: React.ReactNode
}) {
  return (
    <div style={{
      background: COLORS.surface, borderRadius: 6, border: `1px solid ${COLORS.border}`,
      overflow: 'hidden',
    }}>
      <div
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '8px 12px', cursor: 'pointer',
          fontSize: 13, fontWeight: 600, color: COLORS.heading,
        }}
        onClick={() => setOpen(!open)}
      >
        <span>{title} <span style={{ color: COLORS.textMuted, fontWeight: 400 }}>({count})</span></span>
        <span style={{ color: COLORS.textMuted, fontSize: 14 }}>{open ? '\u25b2' : '\u25bc'}</span>
      </div>
      {open && (
        <div style={{ padding: '4px 10px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {children}
        </div>
      )}
    </div>
  )
}

// Clickable item style
function itemStyle(clickable: boolean): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: '6px 10px', borderRadius: 4, fontSize: 13,
    background: COLORS.surface, border: `1px solid ${COLORS.border}`,
  }
  if (clickable) {
    return { ...base, cursor: 'pointer', color: COLORS.accent }
  }
  return base
}

const SmartLinkPanel: React.FC<SmartLinkPanelProps> = ({
  act, section, onNavigate, onNavigateRuling, onNavigateCase,
  rulingsForSection, casesData, commentaryData,
}) => {
  const [relatedSections, setRelatedSections] = useState<RelatedSection[]>([])
  const [definedTerms, setDefinedTerms] = useState<DefinedTerm[]>([])
  const [cases, setCases] = useState<RelatedCase[]>([])
  const [commentary, setCommentary] = useState<RelatedCommentaryItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  // Dropdown open states — all default closed
  const [sectionsOpen, setSectionsOpen] = useState(false)
  const [rulingsOpen, setRulingsOpen] = useState(false)
  const [definedTermsOpen, setDefinedTermsOpen] = useState(false)
  const [casesOpen, setCasesOpen] = useState(false)
  const [commentaryOpen, setCommentaryOpen] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [refs, caseData, commData] = await Promise.all([
          api.sectionRefs(act, section),
          // Use passed-in casesData if provided, else fetch
          casesData
            ? Promise.resolve({ cases: casesData.cases || [] })
            : api.cases(act, section).catch(() => ({ cases: [] })),
          commentaryData
            ? Promise.resolve(Array.isArray(commentaryData) ? { commentary: commentaryData } : commentaryData)
            : api.commentary(act, section).catch(() => ({ commentary: [] })),
        ])
        setRelatedSections(refs.sections || [])

        // Defined terms from section-refs only (italic-matching, not substring matching)
        const refDefs: DefinedTerm[] = (refs.definitions || []).map((d: any) => ({
          term: d.term || d.id || '',
          section: d.section || '',
          anchor: d.anchor || '',
          title: d.title || `s ${d.section}`,
        }))
        // Deduplicate by term (lowercase)
        const seen = new Set<string>()
        setDefinedTerms(refDefs.filter(d => {
          if (seen.has(d.term.toLowerCase())) return false
          seen.add(d.term.toLowerCase())
          return true
        }))

        setCases(caseData.cases || [])
        const commEntries = Array.isArray(commData) ? commData : commData.commentary || []
        setCommentary(commEntries)
      } catch {
        // partial data still better than nothing
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [act, section, casesData, commentaryData])

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

  const handleCaseClick = (c: RelatedCase) => {
    if (onNavigateCase) {
      onNavigateCase(c.citation)
    }
  }

  const rulings = rulingsForSection || []
  const hasContent = relatedSections.length > 0 || definedTerms.length > 0 ||
    rulings.length > 0 || cases.length > 0 || commentary.length > 0

  if (loading) {
    return <div style={{ padding: '12px 0', color: COLORS.textMuted, fontSize: 13 }}>Loading related information...</div>
  }

  if (!hasContent) {
    return null
  }

  // Group sections into same-act and cross-act
  const sameActSections = relatedSections.filter(s => s.act === act)
  const crossActSections = relatedSections.filter(s => s.act !== act)

  // Group cases by court
  const courtOrder = ['HCA', 'FCAFC', 'FCA', 'AATA', 'ARTA']
  const courtLabels: Record<string, string> = {
    HCA: 'High Court', FCAFC: 'Full Federal Court', FCA: 'Federal Court', AATA: 'AAT', ARTA: 'ART',
  }
  const caseGroups: Record<string, RelatedCase[]> = {}
  for (const c of cases) {
    const court = c.court || 'Other'
    if (!caseGroups[court]) caseGroups[court] = []
    caseGroups[court].push(c)
  }

  return (
    <div style={{
      background: COLORS.surface, borderRadius: 8, padding: 12,
      border: `1px solid ${COLORS.border}`, boxShadow: `0 2px 4px rgba(0,0,0,0.2)`,
    }}>
      <h3 style={{ color: COLORS.heading, fontSize: 14, fontWeight: 600, margin: '0 0 12px' }}>Related</h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Sections */}
        {(sameActSections.length > 0 || crossActSections.length > 0) && (
          <CollapsibleGroup
            title="Sections"
            count={sameActSections.length + crossActSections.length}
            open={sectionsOpen}
            setOpen={setSectionsOpen}
          >
            {sameActSections.length > 0 && (
              <>
                <div style={{ color: COLORS.textMuted, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4, marginTop: 2 }}>
                  Same Act
                </div>
                {sameActSections.slice(0, MAX_ITEMS).map((link) => (
                  <div
                    key={'sa-' + link.id}
                    style={itemStyle(true)}
                    onClick={() => handleSectionClick(link)}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                  >
                    s{link.id}{link.title ? ` \u2014 ${link.title}` : ''}
                  </div>
                ))}
              </>
            )}
            {crossActSections.length > 0 && (
              <>
                <div style={{ color: COLORS.textMuted, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4, marginTop: sameActSections.length > 0 ? 8 : 2 }}>
                  Cross-Act
                </div>
                {crossActSections.slice(0, MAX_ITEMS).map((link) => (
                  <div
                    key={'ca-' + link.act + '-' + link.id}
                    style={itemStyle(true)}
                    onClick={() => handleSectionClick(link)}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                  >
                    {shortActName(link.act)} s{link.id}{link.title ? ` \u2014 ${link.title}` : ''}
                  </div>
                ))}
              </>
            )}
          </CollapsibleGroup>
        )}

        {/* Rulings */}
        {rulings.length > 0 && (
          <CollapsibleGroup
            title="Rulings"
            count={rulings.length}
            open={rulingsOpen}
            setOpen={setRulingsOpen}
          >
            {rulings.slice(0, MAX_ITEMS).map((r) => (
              <div
                key={r.citation}
                style={itemStyle(true)}
                onClick={() => handleRulingClick(r)}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
              >
                {r.title || r.citation_display || r.citation}
              </div>
            ))}
          </CollapsibleGroup>
        )}

        {/* Defined Terms */}
        {definedTerms.length > 0 && (
          <CollapsibleGroup
            title="Defined Terms"
            count={definedTerms.length}
            open={definedTermsOpen}
            setOpen={setDefinedTermsOpen}
          >
            {definedTerms.slice(0, MAX_ITEMS).map((def) => (
              <div
                key={def.term}
                style={itemStyle(true)}
                onClick={() => handleDefinitionClick(def)}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
              >
                <span style={{ fontWeight: 500, color: COLORS.text }}>{def.term}</span>
                {' \u2014 '}
                <span style={{ color: COLORS.textMuted }}>defined in {def.title || `s ${def.section}`}</span>
              </div>
            ))}
          </CollapsibleGroup>
        )}

        {/* Cases — grouped by court */}
        {cases.length > 0 && (
          <CollapsibleGroup
            title="Cases"
            count={cases.length}
            open={casesOpen}
            setOpen={setCasesOpen}
          >
            {courtOrder.map(court =>
              caseGroups[court]?.length ? (
                <div key={court} style={{ marginBottom: 8 }}>
                  <div style={{
                    fontSize: 11, fontWeight: 600, color: COLORS.textMuted,
                    fontFamily: "'Montserrat', sans-serif", textTransform: 'uppercase',
                    letterSpacing: '0.5px', marginBottom: 4, padding: '0 10px',
                  }}>
                    {courtLabels[court] || court} ({caseGroups[court].length})
                  </div>
                  {caseGroups[court].slice(0, MAX_ITEMS).map((c, i) => (
                    <div
                      key={c.citation || i}
                      style={{
                        padding: '6px 10px', borderRadius: 4, fontSize: 13,
                        background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                        cursor: 'pointer', color: COLORS.accent, marginBottom: 2,
                      }}
                      onClick={() => handleCaseClick(c)}
                      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                    >
                      <strong>{c.citation}</strong>{c.title ? ` \u2014 ${c.title}` : ''}
                    </div>
                  ))}
                </div>
              ) : null
            )}
            {/* Remaining courts not in courtOrder */}
            {Object.entries(caseGroups)
              .filter(([court]) => !courtOrder.includes(court))
              .map(([court, items]) => (
                <div key={court} style={{ marginBottom: 8 }}>
                  <div style={{
                    fontSize: 11, fontWeight: 600, color: COLORS.textMuted,
                    fontFamily: "'Montserrat', sans-serif", textTransform: 'uppercase',
                    letterSpacing: '0.5px', marginBottom: 4, padding: '0 10px',
                  }}>
                    {court} ({items.length})
                  </div>
                  {items.slice(0, MAX_ITEMS).map((c, i) => (
                    <div
                      key={c.citation || i}
                      style={{
                        padding: '6px 10px', borderRadius: 4, fontSize: 13,
                        background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                        cursor: 'pointer', color: COLORS.accent, marginBottom: 2,
                      }}
                      onClick={() => handleCaseClick(c)}
                      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                    >
                      <strong>{c.citation}</strong>{c.title ? ` \u2014 ${c.title}` : ''}
                    </div>
                  ))}
                </div>
              ))}
          </CollapsibleGroup>
        )}

        {/* Commentary */}
        {commentary.length > 0 && (
          <CollapsibleGroup
            title="Commentary"
            count={commentary.length}
            open={commentaryOpen}
            setOpen={setCommentaryOpen}
          >
            {commentary.slice(0, MAX_ITEMS).map((c, i) => (
              <div
                key={c.paragraph_number || c.heading_title || i}
                style={itemStyle(false)}
              >
                <div>
                  <div style={{ fontWeight: 500, color: COLORS.text, fontSize: 13 }}>{c.heading_title}</div>
                  <div style={{ color: COLORS.textMuted, fontSize: 11, marginTop: 2 }}>
                    {c.publication}{c.paragraph_number ? ` \u00b6 ${c.paragraph_number}` : ''}
                    {c.chapter_title ? ` \u2014 ${c.chapter_title}` : ''}
                  </div>
                </div>
              </div>
            ))}
          </CollapsibleGroup>
        )}
      </div>
    </div>
  )
}

export default SmartLinkPanel