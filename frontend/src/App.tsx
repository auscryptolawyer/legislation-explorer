import React, { useEffect, useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { api } from './api'
import { Tree, PinItem, COLORS } from './components/common/types'
import { TreeNode, findExpandedIds } from './components/TreeNode'
import MCPModal from './components/MCPModal'
import KeyboardShortcuts from './components/KeyboardShortcuts'
import PinnedTabs from './components/PinnedTabs'
import SmartLinkPanel from './components/SmartLinkPanel'
import DefinitionPopover from './components/DefinitionPopover'
import SectionContent from './components/SectionContent'
import RulingContent from './components/RulingContent'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DICT_SECTIONS = new Set(['995-1', '195-1', '6'])

function isDefinitionLink(href?: string) {
  if (!href) return false
  const m = href.match(/\/([a-z0-9-]+)\/s([^#]+)(?:#(.+))?/)
  if (!m) return false
  return DICT_SECTIONS.has(m[2])
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [act, setAct] = useState('itaa-1997')
  const [tree, setTree] = useState<Tree | null>(null)
  const [acts, setActs] = useState<any[]>([])
  const [activeSection, setActiveSection] = useState('')
  const [sectionData, setSectionData] = useState<any>(null)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [error, setError] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  // Sidebar width with localStorage persistence
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('legislation-sidebar-width')
      return saved ? Math.max(280, Math.min(600, parseInt(saved, 10))) : 400
    } catch { return 400 }
  })
  const [isResizing, setIsResizing] = useState(false)

  const [activeRuling, setActiveRuling] = useState<string | null>(null)
  const [rulingData, setRulingData] = useState<any>(null)
  const [commentaryData, setCommentaryData] = useState<any>(null)
  const [casesData, setCasesData] = useState<any>(null)
  const [rulingsForSectionData, setRulingsForSectionData] = useState<any>(null)

  const [mcpOpen, setMcpOpen] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const pickerRef = useRef<HTMLDivElement>(null)
  const [pins, setPins] = useState<PinItem[]>(() => {
    try { return JSON.parse(localStorage.getItem('legislation-pins') || '[]') }
    catch { return [] }
  })

  const [commentaryOpen, setCommentaryOpen] = useState(false)
  const [casesOpen, setCasesOpen] = useState(false)
  const [rulingsOpen, setRulingsOpen] = useState(false)

  // Pins
  const togglePin = () => {
    if (!activeSection || !sectionData) return
    const newPin = { act, section: activeSection, title: sectionData.frontmatter?.title || activeSection }
    const exists = pins.some(p => p.act === act && p.section === activeSection)
    const nextPins = exists
      ? pins.filter(p => !(p.act === act && p.section === activeSection))
      : [...pins, newPin]
    setPins(nextPins)
    localStorage.setItem('legislation-pins', JSON.stringify(nextPins))
  }
  const unpin = (pin: PinItem) => {
    const nextPins = pins.filter(p => !(p.act === pin.act && p.section === pin.section))
    setPins(nextPins)
    localStorage.setItem('legislation-pins', JSON.stringify(nextPins))
  }
  const isPinned = pins.some(p => p.act === act && p.section === activeSection)

  // Definition link popover
  const renderLink = (href?: string, children?: React.ReactNode) => {
    if (!isDefinitionLink(href)) return null
    const m = href!.match(/\/([a-z0-9-]+)\/s([^#]+)(?:#(.+))?/)
    const linkAct = m ? m[1] : act
    return (
      <DefinitionPopover
        act={linkAct}
        href={href}
        onNavigate={(section, anchor) => {
          if (linkAct === act) {
            setActiveSection(section)
            setActiveRuling(null)
            if (anchor) {
              setTimeout(() => {
                const el = document.getElementById(anchor)
                if (el) el.scrollIntoView({ behavior: 'smooth' })
              }, 150)
            }
          }
        }}
      >
        {children}
      </DefinitionPopover>
    )
  }

  // Navigation wrappers for child components
  const onNavigate = (targetAct: string, section: string, anchor?: string) => {
    setAct(targetAct)
    setActiveSection(section)
    setActiveRuling(null)
    if (anchor) {
      setTimeout(() => {
        const el = document.getElementById(anchor)
        if (el) el.scrollIntoView({ behavior: 'smooth' })
      }, 150)
    }
  }
  const onNavigateRuling = (citation: string) => {
    setActiveRuling(citation)
    setActiveSection('')
  }
  const goHome = () => {
    setActiveSection('')
    setActiveRuling(null)
    setSectionData(null)
    window.history.pushState(null, '', '/')
  }

  // Close picker on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node))
        setPickerOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        setShowShortcuts(s => !s)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Mobile detection
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Load acts list
  useEffect(() => {
    api.acts().then(data => setActs(data)).catch(() => setActs([]))
  }, [])

  // Load tree when act changes
  useEffect(() => {
    api.tree(act).then(data => {
      setTree(data)
      setError('')
    }).catch(e => setError(e.message))
    setActiveSection('')
    setSectionData(null)
    setDrawerOpen(false)
  }, [act])

  // Load section / ruling content
  useEffect(() => {
    if (!activeSection && !activeRuling) {
      setSectionData(null)
      setRulingData(null)
      setCommentaryData(null)
      setCasesData(null)
      setRulingsForSectionData(null)
      return
    }

    if (activeRuling) {
      api.ruling(activeRuling)
        .then(data => { setRulingData(data); setError('') })
        .catch(e => { setRulingData(null); setError(e.message) })
      window.history.pushState(null, '', `/rulings/s${activeRuling}`)
    } else if (activeSection) {
      api.section(act, activeSection)
        .then(data => { setSectionData(data); setError('') })
        .catch(e => {
          if (e.message?.includes('404')) {
            setActiveSection('')
            setSectionData(null)
          } else {
            setError(e.message)
          }
        })
      api.commentary(act, activeSection).then(setCommentaryData).catch(() => {})
      api.cases(act, activeSection).then(setCasesData).catch(() => {})
      api.rulings(act, activeSection).then(setRulingsForSectionData).catch(() => {})
      window.history.pushState(null, '', `/${act}/s${activeSection}`)
    }
    if (isMobile) setDrawerOpen(false)
  }, [act, activeSection, activeRuling, isMobile])

  // URL → state sync
  useEffect(() => {
    const handler = () => {
      const sectionMatch = window.location.pathname.match(/\/([a-z0-9-]+)\/s(.+)/)
      const rulingMatch = window.location.pathname.match(/\/rulings\/s(.+)/)
      const actOnlyMatch = window.location.pathname.match(/^\/([a-z0-9-]+)$/)

      if (rulingMatch) {
        setAct('rulings')
        setActiveRuling(decodeURIComponent(rulingMatch[1]))
        setActiveSection('')
      } else if (sectionMatch) {
        setAct(sectionMatch[1])
        setActiveSection(sectionMatch[2])
        setActiveRuling(null)
      } else if (actOnlyMatch) {
        setAct(actOnlyMatch[1])
        setActiveSection('')
        setActiveRuling(null)
      } else {
        setActiveSection('')
        setActiveRuling(null)
      }
    }
    handler()
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  // Resize handlers
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      const newWidth = Math.max(280, Math.min(600, e.clientX))
      setSidebarWidth(newWidth)
      localStorage.setItem('legislation-sidebar-width', String(newWidth))
    }
    const onMouseUp = () => setIsResizing(false)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [isResizing])

  const doSearch = async () => {
    if (!search.trim()) return
    const data = await api.search(search, act)
    setSearchResults(data.results)
  }

  if (error) return <div style={{ padding: 20, color: '#ef4444' }}>Error: {error}</div>
  if (!tree) return <div style={{ padding: 20, color: COLORS.textMuted }}>Loading...</div>

  const mobileSidebarWidth = isMobile ? Math.min(window.innerWidth * 0.85, 380) : sidebarWidth

  return (
    <div style={{ display: 'flex', height: '100vh', background: COLORS.bg }}>
      {/* Mobile hamburger */}
      {isMobile && (
        <button
          onClick={() => setDrawerOpen(!drawerOpen)}
          style={{
            position: 'fixed',
            top: 12,
            left: drawerOpen ? mobileSidebarWidth - 56 : 12,
            zIndex: 110,
            background: COLORS.surface,
            color: COLORS.heading,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 6,
            padding: '10px 12px',
            fontSize: 18,
            cursor: 'pointer',
            lineHeight: 1,
            minWidth: 44,
            minHeight: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'left 0.25s ease',
          }}
        >
          {drawerOpen ? '\u2715' : '\u2630'}
        </button>
      )}

      {/* Mobile backdrop */}
      {isMobile && drawerOpen && (
        <div
          onClick={() => setDrawerOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 90 }}
        />
      )}

      {/* Sidebar */}
      <div style={{
        width: mobileSidebarWidth,
        background: COLORS.surface,
        borderRight: `1px solid ${COLORS.border}`,
        display: 'flex', flexDirection: 'column',
        position: isMobile ? 'fixed' : 'relative',
        left: isMobile ? (drawerOpen ? 0 : -mobileSidebarWidth - 10) : 0,
        top: 0, bottom: 0, zIndex: 100,
        transition: isMobile ? 'left 0.25s ease' : 'none',
      }}>
        <div style={{ padding: isMobile ? '12px 14px' : '14px', borderBottom: `1px solid ${COLORS.border}` }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(() => {
              const currentLabel = acts.find(a => a.id === act)?.name || act
              return (
                <div ref={pickerRef} style={{ position: 'relative' }}>
                  <button onClick={() => setPickerOpen(!pickerOpen)} style={{
                    width: '100%', padding: isMobile ? '8px 10px' : '6px 10px', borderRadius: 6,
                    background: COLORS.bg, color: COLORS.heading,
                    border: `1px solid ${COLORS.border}`, fontSize: 12,
                    fontFamily: "'Montserrat', sans-serif", cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4,
                  }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{currentLabel}</span>
                    <span style={{ fontSize: 9, opacity: 0.6 }}>{pickerOpen ? '▲' : '▼'}</span>
                  </button>
                  {pickerOpen && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 201,
                      marginTop: 4, background: COLORS.surface,
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: 8, padding: '6px 0', maxHeight: 300, overflow: 'auto',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    }}>
                      {(acts.length > 0 ? acts : [{ id: 'itaa-1997', name: 'ITAA 1997' }, { id: 'itaa-1936', name: 'ITAA 1936' }]).map(a => (
                        <button key={a.id} onClick={() => { setPickerOpen(false); goHome(); setAct(a.id) }} style={{
                          display: 'block', width: '100%', padding: '6px 12px',
                          background: 'transparent', border: 'none',
                          color: act === a.id ? COLORS.accent : COLORS.text,
                          fontSize: 12, cursor: 'pointer',
                          fontFamily: "'Montserrat', sans-serif", textAlign: 'left',
                        }}
                          onMouseEnter={e => e.currentTarget.style.background = COLORS.bg}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >{a.name}</button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })()}
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doSearch()}
                placeholder="Search sections..."
                style={{
                  flex: 1, padding: isMobile ? '10px 8px' : 8, borderRadius: 6,
                  background: COLORS.bg, color: COLORS.heading,
                  border: `1px solid ${COLORS.border}`, fontSize: 13,
                  fontFamily: "'Montserrat', sans-serif",
                }}
              />
              <button
                onClick={doSearch}
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
                onClick={() => setMcpOpen(true)}
                style={{
                  padding: isMobile ? '10px 14px' : '8px 14px', borderRadius: 6,
                  background: COLORS.surface, color: COLORS.textMuted,
                  border: `1px solid ${COLORS.border}`, fontSize: 13, cursor: 'pointer',
                  fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
                  whiteSpace: 'nowrap',
                }}
              >
                MCP
              </button>
            </div>
            {searchResults.length > 0 && (
              <div style={{
                maxHeight: 220, overflow: 'auto',
                background: COLORS.bg, borderRadius: 6,
                border: `1px solid ${COLORS.border}`,
              }}>
                {searchResults.map(r => (
                  <div
                    key={`${r.act}-${r.section}`}
                    style={{
                      padding: isMobile ? '8px 10px' : '6px 10px', cursor: 'pointer', fontSize: 12,
                      color: COLORS.text, borderBottom: `1px solid ${COLORS.border}`,
                      fontFamily: "'Montserrat', sans-serif",
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      minHeight: isMobile ? 40 : 32,
                      display: 'flex', alignItems: 'center',
                    }}
                    onClick={() => { setAct(r.act); setActiveSection(r.section); setSearchResults([]) }}
                  >
                    <span style={{ color: COLORS.accent, fontWeight: 600 }}>{r.section}</span>{' '}
                    <span style={{ color: COLORS.textMuted }}>{r.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: isMobile ? '6px 8px' : 8 }}>
          {(tree.parts || []).map(p => (
            <TreeNode key={p.id} node={p} level={0} activeSection={activeSection} onSelect={setActiveSection} isMobile={isMobile} expandedIds={activeSection ? findExpandedIds(tree, activeSection) : new Set()} act={act} />
          ))}
        </div>
      </div>

      {/* Resize handle */}
      {!isMobile && (
        <div
          className={`resize-handle${isResizing ? ' dragging' : ''}`}
          onMouseDown={() => setIsResizing(true)}
          style={{
            width: 4,
            background: isResizing ? '#279e88' : 'transparent',
            position: 'relative',
            zIndex: 101,
            flexShrink: 0,
          }}
        />
      )}

      {/* Main content */}
      <div style={{
        flex: 1, overflow: 'auto',
        padding: isMobile ? '64px 16px 24px' : '28px 40px',
        maxWidth: 960, margin: '0 auto',
        fontFamily: "'Lora', serif",
        color: COLORS.text,
      }}>
        {pins.length > 0 && (
          <PinnedTabs
            pins={pins}
            act={act}
            activeSection={activeSection}
            isMobile={isMobile}
            setAct={setAct}
            setActiveSection={setActiveSection}
            unpin={unpin}
          />
        )}

        {activeRuling && rulingData ? (
          <RulingContent
            rulingData={rulingData}
            isMobile={isMobile}
            renderLink={renderLink}
            onNavigate={onNavigate}
            onNavigateRuling={onNavigateRuling}
          />
        ) : sectionData ? (
          <SectionContent
            act={act}
            sectionData={sectionData}
            commentaryData={commentaryData}
            casesData={casesData}
            rulingsForSectionData={rulingsForSectionData}
            isMobile={isMobile}
            isPinned={isPinned}
            togglePin={togglePin}
            renderLink={renderLink}
            onNavigate={onNavigate}
            onNavigateRuling={onNavigateRuling}
            commentaryOpen={commentaryOpen}
            setCommentaryOpen={setCommentaryOpen}
            casesOpen={casesOpen}
            setCasesOpen={setCasesOpen}
            rulingsOpen={rulingsOpen}
            setRulingsOpen={setRulingsOpen}
          />
        ) : (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            minHeight: '60vh', textAlign: 'center',
            fontFamily: "'Montserrat', sans-serif",
          }}>
            <div style={{ fontSize: 12, color: COLORS.textMuted }}>
              Legislation Explorer <span style={{ opacity: 0.5 }}>v2.3.0</span>
            </div>
            <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              <span style={{ fontSize: 12, color: COLORS.textMuted, opacity: 0.5 }}>Search above or browse the tree</span>
            </div>
          </div>
        )}
      </div>

      <MCPModal open={mcpOpen} onClose={() => setMcpOpen(false)} />
      <KeyboardShortcuts showShortcuts={showShortcuts} setShowShortcuts={setShowShortcuts} />
    </div>
  )
}
