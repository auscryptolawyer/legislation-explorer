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
import TaxCaseContent from './components/TaxCaseContent'
import SettingsPanel from './components/SettingsPanel'
import SearchPanel from './components/SearchPanel'
import { ThemeProvider } from './ThemeContext'
import { shortActName } from './utils/display'

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
  const [browsingAct, setBrowsingAct] = useState(false)

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
  const [searchResultsCount, setSearchResultsCount] = useState(0)
  const pickerRef = useRef<HTMLDivElement>(null)
  const [pins, setPins] = useState<PinItem[]>(() => {
    try { return JSON.parse(localStorage.getItem('legislation-pins') || '[]') }
    catch { return [] }
  })

  const [appInfo, setAppInfo] = useState<any>(null)
  const [user, setUser] = useState<any>(null)
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    api.info().then(setAppInfo).catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/auth/me')
      .then(r => r.ok ? r.json() : null)
      .then(u => { setUser(u); setAuthLoading(false) })
      .catch(() => { setUser(null); setAuthLoading(false) })
  }, [])

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [bugReportOpen, setBugReportOpen] = useState(false)
  const [changelogOpen, setChangelogOpen] = useState(false)
  const [hofOpen, setHofOpen] = useState(false)
  const [hofData, setHofData] = useState<any>(null)
  const [bugReportPending, setBugReportPending] = useState(() => {
    try { return JSON.parse(localStorage.getItem('bugReports') || '[]').length }
    catch { return 0 }
  })
  const settingsRef = useRef<HTMLDivElement>(null)

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
    setBrowsingAct(false)
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
        setBrowsingAct(true)
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
  const hasContent = !!(activeSection || activeRuling || browsingAct)

  return (
    <ThemeProvider>
      <div style={{ display: 'flex', height: '100vh', background: COLORS.bg }}>

      {/* Mobile close button — inside sidebar header (absolute positioned) */}
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
        transform: isMobile
          ? (drawerOpen ? 'translateX(0)' : 'translateX(-101%)')
          : undefined,
        top: 0, bottom: 0, zIndex: 100,
        willChange: isMobile ? 'transform' : undefined,
        transition: isMobile ? 'transform 0.15s ease' : 'none',
      }}>
        {/* Sidebar header: act picker + mobile close button */}
        <div style={{ padding: isMobile ? '12px 14px' : '12px 14px', borderBottom: `1px solid ${COLORS.border}`, position: 'relative' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingRight: isMobile && drawerOpen ? 36 : 0 }}>
            {(() => {
              const currentLabel = shortActName(act)
              return (
                <div ref={pickerRef} style={{ position: 'relative' }}>
                  <button onClick={() => { setPickerOpen(!pickerOpen) }} style={{
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
                        <button key={a.id} onClick={() => { setPickerOpen(false); goHome(); setAct(a.id); setBrowsingAct(true); if (isMobile) setDrawerOpen(false) }} style={{
                          display: 'block', width: '100%', padding: '6px 12px',
                          background: 'transparent', border: 'none',
                          color: act === a.id ? COLORS.accent : COLORS.text,
                          fontSize: 12, cursor: 'pointer',
                          fontFamily: "'Montserrat', sans-serif", textAlign: 'left',
                        }}
                          onMouseEnter={e => e.currentTarget.style.background = COLORS.bg}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >{shortActName(a.id)}</button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
          {isMobile && drawerOpen && (
            <button
              onClick={() => setDrawerOpen(false)}
              style={{
                position: 'absolute', top: 12, right: 14, zIndex: 200,
                background: 'transparent', color: COLORS.heading,
                border: 'none',
                fontSize: 20, cursor: 'pointer', lineHeight: 1,
                width: 36, height: 36,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              {'\u2715'}
            </button>
          )}
        </div>

        {/* Tree */}
        <div style={{ flex: 1, overflow: 'auto', padding: isMobile ? '6px 8px' : 8 }}>
          {(tree.parts || []).map(p => (
            <TreeNode key={p.id} node={p} level={0} activeSection={activeSection} onSelect={e => { setActiveSection(e); if (isMobile) setDrawerOpen(false) }} isMobile={isMobile} expandedIds={activeSection ? findExpandedIds(tree, activeSection) : new Set()} act={act} />
          ))}
        </div>

        {/* Sidebar bottom: settings, bug report, sign in/user */}
        <div style={{
          borderTop: `1px solid ${COLORS.border}`,
          padding: isMobile ? '10px 12px' : '8px 12px',
          display: 'flex', gap: 6, alignItems: 'center',
          flexWrap: 'wrap', justifyContent: 'center',
        }}>
          <div ref={settingsRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setSettingsOpen(true)}
              title="Settings & Tools"
              style={{
                padding: isMobile ? '7px 9px' : '6px 8px', borderRadius: 6,
                background: COLORS.bg,
                color: COLORS.text,
                border: `1px solid ${COLORS.border}`, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                fontSize: 11, fontFamily: "'Montserrat', sans-serif", fontWeight: 500,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
              Settings
            </button>
          </div>
          <button
            onClick={() => setBugReportOpen(true)}
            title="Report a bug"
            style={{
              padding: isMobile ? '7px 9px' : '6px 8px', borderRadius: 6,
              background: COLORS.bg, color: COLORS.textMuted,
              border: `1px solid ${COLORS.border}`, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
              fontSize: 11, fontFamily: "'Montserrat', sans-serif", fontWeight: 500,
              position: 'relative',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="8" y="2" width="8" height="4" rx="1"/><path d="M4 12.5a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6V16a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/><path d="M12 8v8"/><path d="M8 12h8"/>
            </svg>
            {bugReportPending > 0 && (
              <span style={{
                position: 'absolute', top: -4, right: -4,
                background: '#ef4444', color: '#fff',
                borderRadius: 8, padding: '0 5px',
                fontSize: 9, fontWeight: 700, lineHeight: '16px',
                minWidth: 16, textAlign: 'center',
              }}>
                {bugReportPending}
              </span>
            )}
          </button>
          <div style={{ flex: 1, minWidth: 0 }} />
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
              <div style={{
                fontSize: 10, color: COLORS.accent, fontFamily: "'Montserrat', sans-serif",
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {user.name || user.email}
              </div>
              <button
                onClick={() => window.location.href = '/auth/logout'}
                title="Sign out"
                style={{
                  padding: '4px 6px', borderRadius: 4,
                  background: COLORS.bg, color: COLORS.textMuted,
                  border: `1px solid ${COLORS.border}`, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontFamily: "'Montserrat', sans-serif", flexShrink: 0,
                }}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
              </button>
            </div>
          ) : (
            <button
              onClick={() => window.location.href = '/auth/login'}
              title="Sign in"
              style={{
                padding: isMobile ? '7px 9px' : '6px 8px', borderRadius: 6,
                background: COLORS.accent, color: '#fff',
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                fontSize: 11, fontFamily: "'Montserrat', sans-serif", fontWeight: 500,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
              Sign in
            </button>
          )}
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
        padding: isMobile ? '16px 12px 24px' : '20px 40px',
        paddingTop: isMobile ? (hasContent ? 12 : 16) : (hasContent ? 12 : 20),
        maxWidth: 960, margin: '0 auto',
        fontFamily: "'Lora', serif",
        color: COLORS.text,
        display: 'flex', flexDirection: 'column',
        position: 'relative',
      }}>
        {isMobile && !drawerOpen && (
          <button
            onClick={() => setDrawerOpen(true)}
            title="Open sidebar"
            style={{
              position: 'absolute', top: 4, left: 4, zIndex: 60,
              background: COLORS.surface, color: COLORS.heading,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 6, padding: '7px 10px',
              cursor: 'pointer', lineHeight: 1, fontSize: 13,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        )}
        {/* Sticky search bar — only when content is open */}
        {hasContent && (
          <div style={{
            position: 'sticky', top: 0, zIndex: 50,
            background: COLORS.bg,
            padding: '6px 0 10px 0',
            marginBottom: 8,
          }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
              <div style={{ flex: 1 }}>
                <SearchPanel
                  acts={acts}
                  onNavigate={(targetAct, section) => {
                    setAct(targetAct)
                    setActiveSection(section)
                    setActiveRuling(null)
                  }}
                  isMobile={isMobile}
                  onResultsChange={setSearchResultsCount}
                />
              </div>
            </div>
          </div>
        )}

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

        {hasContent && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <button
              onClick={goHome}
              title="Back to tree"
              style={{
                padding: '6px 8px', borderRadius: 6,
                background: COLORS.surface, color: COLORS.textMuted,
                border: `1px solid ${COLORS.border}`, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 11, fontFamily: "'Montserrat', sans-serif",
                fontWeight: 500,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              <span style={{ fontSize: 10, opacity: 0.6 }}>{'<<'}</span>
            </button>
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href).catch(() => {})
              }}
              title="Copy link"
              style={{
                padding: '6px 8px', borderRadius: 6,
                background: COLORS.surface, color: COLORS.textMuted,
                border: `1px solid ${COLORS.border}`, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
            </button>
          </div>
        )}

        {activeRuling && rulingData ? (
          <RulingContent
            rulingData={rulingData}
            isMobile={isMobile}
            renderLink={renderLink}
            onNavigate={onNavigate}
            onNavigateRuling={onNavigateRuling}
          />
        ) : act === 'tax-cases' && sectionData ? (
          <TaxCaseContent
            caseData={sectionData}
            isMobile={isMobile}
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
        ) : browsingAct && tree && act !== 'rulings' && act !== 'tax-cases' ? (
          <div style={{ fontFamily: "'Montserrat', sans-serif" }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <button
                onClick={goHome}
                title="Back to home"
                style={{
                  padding: '6px 8px', borderRadius: 6,
                  background: COLORS.surface, color: COLORS.textMuted,
                  border: `1px solid ${COLORS.border}`, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 4,
                  fontSize: 11, fontFamily: "'Montserrat', sans-serif",
                  fontWeight: 500,
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
                <span style={{ fontSize: 10, opacity: 0.6 }}>{'<<'}</span>
              </button>
              <span style={{ fontSize: 14, fontWeight: 600, color: COLORS.heading }}>
                {shortActName(act)}
              </span>
            </div>
            <div style={{ borderTop: `1px solid ${COLORS.border}`, paddingTop: 8 }}>
              {(() => {
                // Collect all parent IDs to expand everything
                const allIds = new Set<string>()
                const collectIds = (parts: any[]) => {
                  for (const p of parts) {
                    allIds.add(p.id)
                    if (p.divisions) {
                      for (const d of p.divisions) {
                        allIds.add(d.id)
                        if (d.subdivisions) {
                          for (const s of d.subdivisions) {
                            allIds.add(s.id)
                          }
                        }
                      }
                    }
                  }
                }
                collectIds(tree.parts || [])
                return (tree.parts || []).map(p => (
                  <TreeNode key={p.id} node={p} level={0} activeSection={activeSection} onSelect={e => { setActiveSection(e); if (isMobile) setDrawerOpen(false) }} isMobile={isMobile} expandedIds={allIds} act={act} />
                ))
              })()}
            </div>
          </div>
        ) : (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            textAlign: 'center',
            fontFamily: "'Montserrat', sans-serif",
            padding: '0 16px',
            minHeight: searchResultsCount > 0 ? 0 : '60vh',
            justifyContent: searchResultsCount > 0 ? 'flex-start' : 'center',
          }}>
            <div style={{ width: '100%', maxWidth: searchResultsCount > 0 ? '100%' : 400, marginBottom: searchResultsCount > 0 ? 0 : 24 }}>
              <SearchPanel
                acts={acts}
                onNavigate={(targetAct, section) => {
                  setAct(targetAct)
                  setActiveSection(section)
                  setActiveRuling(null)
                }}
                isMobile={isMobile}
                onResultsChange={setSearchResultsCount}
              />
            </div>
            {searchResultsCount === 0 && (
              <>
              <div style={{ fontSize: 11, color: COLORS.textMuted }}>
                Legislation Explorer <span style={{ opacity: 0.5 }}>{appInfo?.version || 'v2.0.0'}</span>
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 20, flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center' }}>
                <button
                  onClick={() => setChangelogOpen(true)}
                  style={{ fontSize: 11, color: COLORS.accent, background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Montserrat', sans-serif" }}
                >
                  Changelog →
                </button>
                <button
                  onClick={() => {
                    setHofOpen(true)
                    api.mcpHallOfFame().then(setHofData).catch(() => {})
                  }}
                  style={{ fontSize: 11, color: COLORS.accent, background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Montserrat', sans-serif" }}
                >
                  Hall of Fame →
                </button>
              </div>
              </>
            )}
          </div>
        )}
      </div>

      <MCPModal open={mcpOpen} onClose={() => setMcpOpen(false)} />
      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      <KeyboardShortcuts showShortcuts={showShortcuts} setShowShortcuts={setShowShortcuts} />

      {/* Bug report modal */}
      {bugReportOpen && (
        <BugReportModal
          onClose={() => setBugReportOpen(false)}
          onReport={(text: string) => {
            try {
              const reports = JSON.parse(localStorage.getItem('bugReports') || '[]')
              reports.push({ text, time: new Date().toISOString(), url: window.location.href })
              localStorage.setItem('bugReports', JSON.stringify(reports))
              setBugReportPending(reports.length)
            } catch {}
            setBugReportOpen(false)
          }}
        />
      )}

      {/* Changelog modal */}
      {changelogOpen && appInfo?.changelog && (
        <ModalOverlay onClose={() => setChangelogOpen(false)}>
          <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.heading, marginBottom: 16, fontFamily: "'Montserrat', sans-serif" }}>
            Changelog
          </div>
          <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
            {appInfo.changelog.map((entry: any, i: number) => (
              <div key={i} style={{ marginBottom: 16, paddingBottom: 16, borderBottom: i < appInfo.changelog.length - 1 ? `1px solid ${COLORS.border}` : 'none' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.accent, marginBottom: 2, fontFamily: "'Montserrat', sans-serif" }}>
                  v{entry.version} — {entry.date}
                </div>
                <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 6, fontFamily: "'Montserrat', sans-serif" }}>
                  {entry.title}
                </div>
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: COLORS.text, fontFamily: "'Montserrat', sans-serif", lineHeight: 1.6 }}>
                  {entry.changes.map((c: string, j: number) => (
                    <li key={j}>{c}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </ModalOverlay>
      )}

      {/* Hall of Fame modal */}
      {hofOpen && (
        <ModalOverlay onClose={() => setHofOpen(false)}>
          <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.heading, marginBottom: 16, fontFamily: "'Montserrat', sans-serif" }}>
            MCP Hall of Fame
          </div>
          {hofData ? (
            <div style={{ maxHeight: '60vh', overflow: 'auto', fontSize: 12, color: COLORS.text, fontFamily: "'Montserrat', sans-serif" }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, lineHeight: 1.5, color: COLORS.textMuted }}>
                {JSON.stringify(hofData, null, 2)}
              </pre>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: COLORS.textMuted, fontFamily: "'Montserrat', sans-serif" }}>
              Loading...
            </div>
          )}
        </ModalOverlay>
      )}
    </div>
    </ThemeProvider>
  )
}

// ---------------------------------------------------------------------------
// ModalOverlay — shared backdrop + container
// ---------------------------------------------------------------------------

function ModalOverlay({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: COLORS.surface, borderRadius: 12,
          padding: 24, width: '90%', maxWidth: 520,
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
        }}
      >
        {children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// BugReportModal
// ---------------------------------------------------------------------------

function BugReportModal({ onClose, onReport }: { onClose: () => void; onReport: (text: string) => void }) {
  const [text, setText] = useState('')

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: COLORS.surface, borderRadius: 12,
          padding: 24, width: '90%', maxWidth: 480,
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.heading, marginBottom: 12, fontFamily: "'Montserrat', sans-serif" }}>
          Report a Bug
        </div>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Describe what went wrong..."
          rows={4}
          style={{
            width: '100%', padding: 10, borderRadius: 6,
            background: COLORS.bg, color: COLORS.heading,
            border: `1px solid ${COLORS.border}`, fontSize: 13,
            fontFamily: "'Montserrat', sans-serif", resize: 'vertical',
            outline: 'none',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', borderRadius: 6,
              background: COLORS.bg, color: COLORS.text,
              border: `1px solid ${COLORS.border}`, cursor: 'pointer',
              fontSize: 12, fontFamily: "'Montserrat', sans-serif",
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => { if (text.trim()) onReport(text.trim()) }}
            disabled={!text.trim()}
            style={{
              padding: '8px 16px', borderRadius: 6,
              background: text.trim() ? COLORS.accent : COLORS.border,
              color: text.trim() ? '#fff' : COLORS.textMuted,
              border: 'none', cursor: text.trim() ? 'pointer' : 'default',
              fontSize: 12, fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
            }}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  )
}