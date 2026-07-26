import React, { useEffect, useRef, useState } from 'react'
import { COLORS } from './common/types'
import { api } from '../api'
import { shortActName } from '../utils/display'

const PAGE_SIZE = 25

interface FlatResult {
  act: string
  act_name: string
  section: string
  title: string
  headline: string
  match_type: string
  score: number
  snippet?: string
  type?: string
}

interface SearchPanelProps {
  acts: { id: string; name: string }[]
  onNavigate: (act: string, section: string) => void
  isMobile: boolean
  onResultsChange?: (count: number) => void
}

export default function SearchPanel({ acts, onNavigate, isMobile, onResultsChange }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FlatResult[]>([])
  const [unfilteredResults, setUnfilteredResults] = useState<FlatResult[]>([])
  const [autoResults, setAutoResults] = useState<FlatResult[]>([])
  const [filterOpen, setFilterOpen] = useState(false)
  const [sortMode, setSortMode] = useState<'bestmatch' | 'bysection' | 'byact'>('bestmatch')
  const [loading, setLoading] = useState(false)
  const [autoLoading, setAutoLoading] = useState(false)
  const [selectedActs, setSelectedActs] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(0)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const inputRef = useRef<HTMLInputElement>(null)
  const autoRef = useRef<HTMLDivElement>(null)

  // Autocomplete
  useEffect(() => {
    const q = query.trim()
    if (!q || q.length < 2) {
      setAutoResults([])
      return
    }
    setAutoLoading(true)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await api.searchFlat(q, 8)
        setAutoResults(data.results || data || [])
      } catch {
        setAutoResults([])
      }
      setAutoLoading(false)
    }, 250)
    return () => clearTimeout(debounceRef.current)
  }, [query])

  // Close autocomplete on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (autoRef.current && !autoRef.current.contains(e.target as Node))
        setAutoResults([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Re-filter results when source selection changes
  useEffect(() => {
    if (unfilteredResults.length === 0) return
    const filtered = selectedActs.size > 0
      ? unfilteredResults.filter(r => selectedActs.has(r.act))
      : unfilteredResults
    setResults(filtered)
    setCurrentPage(0)
  }, [selectedActs, unfilteredResults])

  // Notify parent of results count
  useEffect(() => {
    onResultsChange?.(results.length)
  }, [results.length, onResultsChange])

  const doSearch = async (q?: string) => {
    const term = (q || query).trim()
    if (!term) return

    setLoading(true)
    try {
      if (sortMode === 'bestmatch') {
        const data = await api.searchFlat(term, 200)
        const allResults: FlatResult[] = data.results || data || []
        setUnfilteredResults(allResults)
        if (selectedActs.size > 0) {
          setResults(allResults.filter(r => selectedActs.has(r.act)))
        } else {
          setResults(allResults)
        }
      } else {
        // Per-act search
        const targets = selectedActs.size > 0
          ? acts.filter(a => selectedActs.has(a.id))
          : acts
        const all: FlatResult[] = []
        for (const a of targets) {
          try {
            const data = await api.search(term, a.id)
            if (data.results) {
              all.push(...data.results.map((r: any) => ({
                act: a.id,
                act_name: a.name,
                section: r.section,
                title: r.title,
                headline: '',
                match_type: '',
                score: 0,
              })))
            }
          } catch { /* skip */ }
        }
        setUnfilteredResults(all)
        setResults(all)
      }
    } catch { setResults([]) }
    setLoading(false)
    setAutoResults([])
    setCurrentPage(0)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      doSearch()
    }
  }

  const handleSelect = (r: FlatResult) => {
    setQuery('')
    setResults([])
    setAutoResults([])
    if (r.section) {
      onNavigate(r.act, r.section)
    }
  }

  const toggleAct = (id: string) => {
    const next = new Set(selectedActs)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedActs(next)
  }

  // Pagination calculations
  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE))
  const pageStart = currentPage * PAGE_SIZE
  const pageResults = results.slice(pageStart, pageStart + PAGE_SIZE)

  const filterButtonSvg = (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="2" y1="3" x2="14" y2="3" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="13" x2="14" y2="13" />
    </svg>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', position: 'relative' }}>
      {/* Search input row */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
        <div ref={autoRef} style={{ position: 'relative', flex: 1 }}>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search legislation..."
            style={{
              width: '100%',
              padding: isMobile ? '10px 10px' : '8px 10px',
              borderRadius: 6,
              background: COLORS.bg,
              color: COLORS.heading,
              border: `1px solid ${COLORS.border}`,
              fontSize: 13,
              fontFamily: "'Montserrat', sans-serif",
              outline: 'none',
            }}
          />
          {/* Autocomplete dropdown */}
          {autoResults.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 300,
              marginTop: 2, background: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 6, maxHeight: 240, overflow: 'auto',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              {autoResults.map((r, i) => (
                <div
                  key={`${r.act}-${r.section}-${i}`}
                  onClick={() => { handleSelect(r); inputRef.current?.focus() }}
                  style={{
                    padding: '7px 10px', cursor: 'pointer', fontSize: 12,
                    color: COLORS.text, borderBottom: `1px solid ${COLORS.border}`,
                    fontFamily: "'Montserrat', sans-serif",
                    display: 'flex', alignItems: 'center', gap: 6,
                    minHeight: isMobile ? 40 : 0,
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = COLORS.bg}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span style={{
                    fontSize: 10, color: COLORS.accent, fontWeight: 600,
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}>
                    {r.act === 'rulings' ? r.section : r.act.startsWith('master-') ? shortActName(r.act) : `${shortActName(r.act)} s${r.section}`}
                  </span>
                  <span style={{ color: COLORS.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.title}
                  </span>
                </div>
              ))}
            </div>
          )}
          {autoLoading && (
            <div style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: COLORS.textMuted, fontSize: 10 }}>
              ...
            </div>
          )}
        </div>
        <button
          onClick={() => doSearch()}
          style={{
            padding: isMobile ? '10px 14px' : '8px 14px', borderRadius: 6,
            background: COLORS.accent, color: '#fff',
            border: 'none', fontSize: 13, cursor: 'pointer',
            fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
            whiteSpace: 'nowrap',
          }}
        >
          Search
        </button>
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          title="Filters"
          style={{
            padding: isMobile ? '10px 12px' : '8px 12px', borderRadius: 6,
            background: filterOpen ? COLORS.accent : COLORS.surface,
            color: filterOpen ? '#fff' : COLORS.textMuted,
            border: `1px solid ${filterOpen ? COLORS.accent : COLORS.border}`,
            fontSize: 13, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: "'Montserrat', sans-serif",
          }}
        >
          {filterButtonSvg}
        </button>
      </div>

      {/* Filters panel — absolutely positioned dropdown */}
      {filterOpen && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 300,
          marginTop: 2, background: COLORS.bg, borderRadius: 6,
          border: `1px solid ${COLORS.border}`,
          padding: 10,
          display: 'flex', flexDirection: 'column', gap: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          <div style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif" }}>Sort:</div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {(['bestmatch', 'bysection', 'byact'] as const).map(mode => (
              <label
                key={mode}
                style={{
                  fontSize: 11, color: COLORS.text, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 6px', borderRadius: 4,
                  background: sortMode === mode ? COLORS.accent + '22' : 'transparent',
                  fontFamily: "'Montserrat', sans-serif",
                }}
              >
                <input
                  type="radio"
                  name="sortMode"
                  checked={sortMode === mode}
                  onChange={() => setSortMode(mode)}
                  style={{ margin: 0 }}
                />
                {mode === 'bestmatch' ? 'Best match' : mode === 'bysection' ? 'By section' : 'By act'}
              </label>
            ))}
          </div>
          <div style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif" }}>Sources:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {acts.map(a => (
              <label
                key={a.id}
                style={{
                  fontSize: 11, color: COLORS.text, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 6px', borderRadius: 4,
                  background: selectedActs.has(a.id) ? COLORS.accent + '22' : 'transparent',
                  fontFamily: "'Montserrat', sans-serif",
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedActs.has(a.id)}
                  onChange={() => toggleAct(a.id)}
                  style={{ margin: 0 }}
                />
                {shortActName(a.id)}
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {loading && (
        <div style={{ padding: '8px 4px', fontSize: 12, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif" }}>
          Searching...
        </div>
      )}
      {results.length > 0 && !loading && (
        <>
          {/* Results header */}
          <div style={{
            fontSize: 10, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif",
            padding: '4px 2px', borderBottom: `1px solid ${COLORS.border}`,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span>{results.length} result{results.length !== 1 ? 's' : ''} — Page {currentPage + 1} of {totalPages}</span>
          </div>

          {/* Results list */}
          <div style={{
            background: COLORS.bg, borderRadius: 6,
            border: `1px solid ${COLORS.border}`,
            textAlign: 'left',
          }}>
            {pageResults.map((r, i) => {
              const isRuling = r.type === 'ruling' || r.act === 'rulings'
              const isCchGuide = r.act.startsWith('master-')
              const sourceLabel = isRuling
                ? (r.type === 'ruling' ? 'Ruling' : 'ATO ID')
                : shortActName(r.act)
              const sectionDisplay = isRuling
                ? r.section
                : isCchGuide
                  ? shortActName(r.act)
                  : `${shortActName(r.act)} s${r.section}`
              return (
              <div
                key={`${r.act}-${r.section}-${pageStart + i}`}
                onClick={() => handleSelect(r)}
                style={{
                  padding: isMobile ? '10px 12px' : '8px 12px', cursor: 'pointer', fontSize: 12,
                  color: COLORS.text, borderBottom: `1px solid ${COLORS.border}`,
                  fontFamily: "'Montserrat', sans-serif",
                }}
                onMouseEnter={e => e.currentTarget.style.background = COLORS.accent + '11'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: 11, color: COLORS.accent, fontWeight: 600,
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}>
                    {sectionDisplay}
                  </span>
                  {r.title && r.title !== r.section && (
                    <span style={{
                      color: COLORS.textMuted,
                      wordBreak: 'break-word', overflowWrap: 'break-word',
                    }}>
                      {r.title}
                    </span>
                  )}
                </div>
                {r.snippet && (
                  <div style={{
                    fontSize: 11, color: COLORS.textMuted, opacity: 0.7,
                    marginTop: 3, paddingLeft: 2,
                    fontFamily: "'Lora', serif",
                    lineHeight: 1.4, textAlign: 'left',
                  }}
                    dangerouslySetInnerHTML={{ __html: r.snippet }}
                  />
                )}
                <div style={{ fontSize: 9, color: COLORS.textMuted, opacity: 0.5, marginTop: 2, textAlign: 'left' }}>
                  {sourceLabel}
                </div>
              </div>
            )})}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8,
              padding: '8px 0',
            }}>
              <button
                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                disabled={currentPage === 0}
                style={{
                  padding: '6px 12px', borderRadius: 6,
                  background: currentPage === 0 ? COLORS.bg : COLORS.surface,
                  color: currentPage === 0 ? COLORS.textMuted : COLORS.text,
                  border: `1px solid ${COLORS.border}`,
                  cursor: currentPage === 0 ? 'default' : 'pointer',
                  fontSize: 11, fontFamily: "'Montserrat', sans-serif",
                }}
              >
                ← Previous
              </button>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                // Show pages around current
                const start = Math.max(0, Math.min(currentPage - 3, totalPages - 7))
                const pageNum = start + i
                if (pageNum >= totalPages) return null
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    style={{
                      width: 28, height: 28, borderRadius: 4,
                      background: pageNum === currentPage ? COLORS.accent : 'transparent',
                      color: pageNum === currentPage ? '#fff' : COLORS.textMuted,
                      border: pageNum === currentPage ? 'none' : `1px solid ${COLORS.border}`,
                      cursor: 'pointer', fontSize: 11,
                      fontFamily: "'Montserrat', sans-serif",
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    {pageNum + 1}
                  </button>
                )
              })}
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={currentPage >= totalPages - 1}
                style={{
                  padding: '6px 12px', borderRadius: 6,
                  background: currentPage >= totalPages - 1 ? COLORS.bg : COLORS.surface,
                  color: currentPage >= totalPages - 1 ? COLORS.textMuted : COLORS.text,
                  border: `1px solid ${COLORS.border}`,
                  cursor: currentPage >= totalPages - 1 ? 'default' : 'pointer',
                  fontSize: 11, fontFamily: "'Montserrat', sans-serif",
                }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}