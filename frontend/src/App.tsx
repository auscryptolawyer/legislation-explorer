import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { api } from './api'

type Section = { id: string; title: string; path: string }
type Subdivision = { id: string; title: string; sections: Section[] }
type Division = { id: string; title: string; subdivisions: Subdivision[]; sections: Section[] }
type Part = { id: string; title: string; divisions: Division[]; sections: Section[] }
type Tree = { act: string; parts: Part[] }

// Cadena Legal brand palette
const COLORS = {
  bg: '#0a1214',
  surface: '#0b1b1f',
  surfaceHover: '#141e20',
  border: '#253d3d',
  text: '#aebec2',
  textMuted: '#758696',
  accent: '#279e88',
  accentHover: '#1f5858',
  heading: '#ffffff',
}

function TreeNode({ node, level, activeSection, onSelect, isMobile }: {
  node: Part | Division | Subdivision | Section
  level: number
  activeSection: string
  onSelect: (id: string) => void
  isMobile: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const isSection = 'path' in node
  const isPart = 'divisions' in node
  const isDivision = 'subdivisions' in node && 'sections' in node && !isPart
  const isSubdivision = 'sections' in node && !('subdivisions' in node) && !isPart && !isSection
  const hasChildren = !isSection && (
    (isPart && (((node as Part).divisions || []).length > 0 || ((node as Part).sections || []).length > 0)) ||
    (isDivision && (((node as Division).subdivisions || []).length > 0 || ((node as Division).sections || []).length > 0)) ||
    (isSubdivision && ((node as Subdivision).sections || []).length > 0)
  )

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setExpanded(!expanded)
  }

  const displayId = isSection ? (node as Section).id : (node as Part | Division | Subdivision).id
  const displayTitle = isSection
    ? (node as Section).title
    : (node as Part | Division | Subdivision).title

  const indent = isMobile ? Math.min(level * 10, 40) : level * 14

  return (
    <div style={{ marginLeft: indent }}>
      <div
        style={{
          padding: isMobile ? '6px 8px' : '4px 6px',
          cursor: 'pointer',
          borderRadius: 4,
          background: isSection && (node as Section).id === activeSection ? 'rgba(39,158,136,0.12)' : 'transparent',
          color: isSection ? COLORS.text : COLORS.textMuted,
          fontWeight: isSection ? 400 : 500,
          fontSize: isMobile ? 13 : 12,
          fontFamily: "'Montserrat', sans-serif",
          display: 'flex',
          alignItems: 'center',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          minHeight: isMobile ? 36 : 28,
        }}
        onClick={() => {
          if (isSection) onSelect((node as Section).id)
          else setExpanded(!expanded)
        }}
      >
        {hasChildren && (
          <span onClick={toggle} style={{
            width: 20, display: 'inline-block', textAlign: 'center', fontSize: 8,
            color: COLORS.textMuted, flexShrink: 0,
          }}>
            {expanded ? '\u25bc' : '\u25b6'}
          </span>
        )}
        {!hasChildren && <span style={{ width: 20, display: 'inline-block', flexShrink: 0 }} />}
        <span style={{ marginLeft: 4, whiteSpace: 'nowrap', flexShrink: 0, color: COLORS.heading }}>{displayId}</span>
        {displayTitle && (
          <span style={{ marginLeft: 6, opacity: 0.65, fontWeight: 400, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            — {displayTitle}
          </span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {isPart && ((node as Part).divisions || []).map(d => (
            <TreeNode key={d.id} node={d} level={level + 1} activeSection={activeSection} onSelect={onSelect} isMobile={isMobile} />
          ))}
          {isPart && ((node as Part).sections || []).map(s => (
            <TreeNode key={s.id} node={s} level={level + 1} activeSection={activeSection} onSelect={onSelect} isMobile={isMobile} />
          ))}
          {isDivision && ((node as Division).sections || []).map(s => (
            <TreeNode key={s.id} node={s} level={level + 1} activeSection={activeSection} onSelect={onSelect} isMobile={isMobile} />
          ))}
          {isDivision && ((node as Division).subdivisions || []).map(s => (
            <TreeNode key={s.id} node={s} level={level + 1} activeSection={activeSection} onSelect={onSelect} isMobile={isMobile} />
          ))}
          {isSubdivision && ((node as Subdivision).sections || []).map(s => (
            <TreeNode key={s.id} node={s} level={level + 1} activeSection={activeSection} onSelect={onSelect} isMobile={isMobile} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [act, setAct] = useState('itaa-1997')
  const [tree, setTree] = useState<Tree | null>(null)
  const [activeSection, setActiveSection] = useState('')
  const [sectionData, setSectionData] = useState<any>(null)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [error, setError] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    api.tree(act).then(setTree).catch(e => setError(e.message))
    setActiveSection('')
    setSectionData(null)
    setDrawerOpen(false)
  }, [act])

  useEffect(() => {
    if (!activeSection) return
    api.section(act, activeSection)
      .then(setSectionData)
      .catch(e => setError(e.message))
    window.history.pushState(null, '', `/${act}/s${activeSection}`)
    if (isMobile) setDrawerOpen(false)
  }, [act, activeSection, isMobile])

  useEffect(() => {
    const handler = () => {
      const m = window.location.pathname.match(/\/(itaa-\d{4})\/s(.+)/)
      if (m) {
        setAct(m[1])
        setActiveSection(m[2])
      }
    }
    handler()
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const doSearch = async () => {
    if (!search.trim()) return
    const data = await api.search(search, act)
    setSearchResults(data.results)
  }

  if (error) return <div style={{ padding: 20, color: '#ef4444' }}>Error: {error}</div>
  if (!tree) return <div style={{ padding: 20, color: COLORS.textMuted }}>Loading...</div>

  const sidebarWidth = isMobile ? 280 : 400

  return (
    <div style={{ display: 'flex', height: '100vh', background: COLORS.bg }}>
      {/* Mobile hamburger */}
      {isMobile && (
        <button
          onClick={() => setDrawerOpen(!drawerOpen)}
          style={{
            position: 'fixed', top: 12, left: 12, zIndex: 110,
            background: COLORS.surface, color: COLORS.heading,
            border: `1px solid ${COLORS.border}`, borderRadius: 6,
            padding: '10px 12px', fontSize: 18, cursor: 'pointer',
            lineHeight: 1, minWidth: 44, minHeight: 44,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          {drawerOpen ? '\u2715' : '\u2630'}
        </button>
      )}

      {/* Backdrop on mobile */}
      {isMobile && drawerOpen && (
        <div
          onClick={() => setDrawerOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            zIndex: 90,
          }}
        />
      )}

      {/* Sidebar / Drawer */}
      <div style={{
        width: sidebarWidth,
        background: COLORS.surface,
        borderRight: `1px solid ${COLORS.border}`,
        display: 'flex', flexDirection: 'column',
        position: isMobile ? 'fixed' : 'relative',
        left: isMobile ? (drawerOpen ? 0 : -sidebarWidth - 10) : 0,
        top: 0, bottom: 0, zIndex: 100,
        transition: 'left 0.25s ease',
      }}>
        <div style={{ padding: isMobile ? '12px 14px' : '14px', borderBottom: `1px solid ${COLORS.border}` }}>
          <select
            value={act}
            onChange={e => {
              setActiveSection('')
              setSectionData(null)
              setAct(e.target.value)
            }}
            style={{
              width: '100%', padding: isMobile ? '10px 8px' : 8, borderRadius: 6,
              background: COLORS.bg, color: COLORS.heading,
              border: `1px solid ${COLORS.border}`, fontSize: 13,
              fontFamily: "'Montserrat', sans-serif",
            }}
          >
            <option value="itaa-1997">ITAA 1997</option>
            <option value="itaa-1936">ITAA 1936</option>
          </select>
          <div style={{ display: 'flex', marginTop: 10, gap: 6 }}>
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
          </div>
          {searchResults.length > 0 && (
            <div style={{
              maxHeight: 220, overflow: 'auto', marginTop: 10,
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
        <div style={{ flex: 1, overflow: 'auto', padding: isMobile ? '6px 8px' : 8 }}>
          {(tree.parts || []).map(p => (
            <TreeNode key={p.id} node={p} level={0} activeSection={activeSection} onSelect={setActiveSection} isMobile={isMobile} />
          ))}
        </div>
      </div>

      {/* Main content */}
      <div style={{
        flex: 1, overflow: 'auto',
        padding: isMobile ? '64px 16px 24px' : '28px 40px',
        maxWidth: 960, margin: '0 auto',
        fontFamily: "'Lora', serif",
        color: COLORS.text,
      }}>
        {sectionData ? (
          <div>
            <div style={{
              marginBottom: 20, color: COLORS.textMuted, fontSize: 12,
              fontFamily: "'Montserrat', sans-serif", letterSpacing: 0.3,
              textTransform: 'uppercase' as const,
            }}>
              {sectionData.frontmatter.act} &rsaquo; Part {sectionData.frontmatter.part} &rsaquo; Division {sectionData.frontmatter.division}
            </div>
            <div style={{
              lineHeight: 1.7, fontSize: isMobile ? 15 : 15, color: COLORS.text,
            }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  h1: ({ children }) => <h1 style={{ color: COLORS.heading, fontSize: isMobile ? 20 : 22, marginBottom: 16, fontWeight: 600, borderBottom: `1px solid ${COLORS.border}`, paddingBottom: 8 }}>{children}</h1>,
                  h2: ({ children }) => <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, marginTop: 24, marginBottom: 12, fontWeight: 600 }}>{children}</h2>,
                  h3: ({ children }) => <h3 style={{ color: COLORS.heading, fontSize: isMobile ? 15 : 16, marginTop: 20, marginBottom: 10, fontWeight: 600 }}>{children}</h3>,
                  p: ({ children }) => <p style={{ marginBottom: 12, color: COLORS.text }}>{children}</p>,
                  a: ({ children, href }) => <a href={href} style={{ color: COLORS.accent, textDecoration: 'none' }}>{children}</a>,
                  blockquote: ({ children }) => <blockquote style={{ marginLeft: 16, paddingLeft: 12, borderLeft: `3px solid ${COLORS.border}`, color: COLORS.textMuted }}>{children}</blockquote>,
                  ul: ({ children }) => <ul style={{ marginLeft: 20, marginBottom: 12 }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ marginLeft: 20, marginBottom: 12 }}>{children}</ol>,
                  li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                }}
              >
                {sectionData.markdown}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div style={{ color: COLORS.textMuted, fontSize: 14 }}>
            Select a section from the tree.
          </div>
        )}
      </div>
    </div>
  )
}
