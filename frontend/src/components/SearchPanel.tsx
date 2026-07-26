import React, { useEffect, useRef, useState } from 'react'
import { COLORS } from './common/types'
import { api } from '../api'
import { shortActName } from '../utils/display'

interface FlatResult {
  act: string
  act_name: string
  section: string
  title: string
  headline: string
  match_type: string
  score: number
}

interface SearchPanelProps {
  acts: { id: string; name: string }[]
  onNavigate: (act: string, section: string) => void
  isMobile: boolean
}

export default function SearchPanel({ acts, onNavigate, isMobile }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FlatResult[]>([])
  const [autoResults, setAutoResults] = useState<FlatResult[]>([])
  const [filterOpen, setFilterOpen] = useState(false)
  const [bestMatch, setBestMatch] = useState(true)
  const [loading, setLoading] = useState(false)
  const [autoLoading, setAutoLoading] = useState(false)
  const [selectedActs, setSelectedActs] = useState<Set<string>>(new Set())
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

  const doSearch = async (q?: string) => {
    const term = (q || query).trim()
    if (!term) return

    setLoading(true)
    try {
      if (bestMatch) {
        const data = await api.searchFlat(term)
        const allResults: FlatResult[] = data.results || data || []
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
        setResults(all)
      }
    } catch { setResults([]) }
    setLoading(false)
    setAutoResults([])
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

  const filterButtonSvg = (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="2" y1="3" x2="14" y2="3" />
      <line x1="2" y1="8" x2="14" y2="8" />
      <line x1="2" y1="13" x2="14" y2="13" />
    </svg>
  )

  const agentIcon = (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
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
                    {shortActName(r.act)} s{r.section}
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

      {/* Filters panel */}
      {filterOpen && (
        <div style={{
          background: COLORS.bg, borderRadius: 6,
          border: `1px solid ${COLORS.border}`,
          padding: 10,
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <label style={{ fontSize: 12, color: COLORS.text, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontFamily: "'Montserrat', sans-serif" }}>
              <input
                type="checkbox"
                checked={bestMatch}
                onChange={() => setBestMatch(!bestMatch)}
              />
              Best matches (cross-act ranking)
            </label>
          </div>
          {!bestMatch && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 2, fontFamily: "'Montserrat', sans-serif" }}>Sources:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {acts.map(a => (
                  <label
                    key={a.id}
                    style={{
                      fontSize: 11, color: COLORS.text, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 4,
                      padding: '2px 6px', borderRadius: 4,
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
        </div>
      )}

      {/* Results */}
      {loading && (
        <div style={{ padding: '8px 4px', fontSize: 12, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif" }}>
          Searching...
        </div>
      )}
      {results.length > 0 && !loading && (
        <div style={{
          maxHeight: 300, overflow: 'auto',
          background: COLORS.bg, borderRadius: 6,
          border: `1px solid ${COLORS.border}`,
        }}>
          {results.map((r, i) => (
            <div
              key={`${r.act}-${r.section}-${i}`}
              onClick={() => handleSelect(r)}
              style={{
                padding: isMobile ? '8px 10px' : '6px 10px', cursor: 'pointer', fontSize: 12,
                color: COLORS.text, borderBottom: `1px solid ${COLORS.border}`,
                fontFamily: "'Montserrat', sans-serif",
                minHeight: isMobile ? 40 : 32,
                display: 'flex', alignItems: 'center', gap: 6,
              }}
              onMouseEnter={e => e.currentTarget.style.background = COLORS.accent + '11'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{
                fontSize: 10, color: COLORS.accent, fontWeight: 600,
                whiteSpace: 'nowrap', flexShrink: 0,
              }}>
                {shortActName(r.act)} s{r.section}
              </span>
              <span style={{
                color: COLORS.textMuted, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {r.title || r.headline}
              </span>
              {bestMatch && r.score > 0 && (
                <span style={{ fontSize: 9, color: COLORS.textMuted, opacity: 0.5, marginLeft: 'auto', flexShrink: 0 }}>
                  {Math.round(r.score)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
