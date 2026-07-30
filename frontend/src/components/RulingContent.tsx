import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { COLORS } from './common/types'
import { createMarkdownComponents } from './MarkdownRenderers'
import { shortActName } from '../utils/display'
import { api } from '../api'

type RulingContentProps = {
  rulingData: any
  isMobile: boolean
  renderLink?: (href?: string, children?: React.ReactNode) => React.ReactNode | null
  onNavigate: (act: string, section: string, anchor?: string) => void
  onNavigateRuling: (citation: string) => void
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function extractHeaderText(node: React.ReactNode): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractHeaderText).join('')
  if (React.isValidElement(node)) {
    const children = (node.props as any)?.children
    return children ? extractHeaderText(children) : ''
  }
  return ''
}

type TocItem = { level: number; text: string; id: string }

function parseToc(body: string): TocItem[] {
  const items: TocItem[] = []
  const re = /^(#{2,3})\s+(.+)$/gm
  let match
  while ((match = re.exec(body)) !== null) {
    const level = match[1].length // 2 for h2, 3 for h3
    const text = match[2].replace(/\*{1,2}|`{1,2}|\[([^\]]*)\]\([^)]+\)/g, '$1').trim()
    const id = slugify(text)
    items.push({ level, text, id })
  }
  return items
}

type RelatedCase = {
  citation: string
  title: string
  court?: string
  year?: string
}

export default function RulingContent({
  rulingData,
  isMobile,
  renderLink,
  onNavigate,
  onNavigateRuling,
}: RulingContentProps) {
  const fm = rulingData?.frontmatter || {}
  const body: string = rulingData?.body || ''
  const descriptiveTitle: string = rulingData?.descriptive_title || ''
  const baseComponents = createMarkdownComponents(isMobile, 'rulings', onNavigate, onNavigateRuling, renderLink)

  // Parse table of contents from ##/### headers
  const toc = parseToc(body)

  // Override h2/h3 to include anchor IDs
  const components = {
    ...baseComponents,
    h2: ({ children, ...rest }: { children?: React.ReactNode; [key: string]: any }) => {
      const text = extractHeaderText(children)
      const id = slugify(text)
      const base = baseComponents.h2({ children })
      return React.cloneElement(base as React.ReactElement, { id, ...rest }, children)
    },
    h3: ({ children, ...rest }: { children?: React.ReactNode; [key: string]: any }) => {
      const text = extractHeaderText(children)
      const id = slugify(text)
      const base = baseComponents.h3({ children })
      return React.cloneElement(base as React.ReactElement, { id, ...rest }, children)
    },
  }

  // Summary collapsible state
  const [summaryOpen, setSummaryOpen] = useState(false)

  // Related cases state
  const [relatedCases, setRelatedCases] = useState<RelatedCase[]>([])
  const [relatedLoading, setRelatedLoading] = useState(false)

  useEffect(() => {
    const refs = rulingData?.referenced_sections || []
    if (refs.length === 0) {
      setRelatedCases([])
      return
    }
    setRelatedLoading(true)
    const seen = new Set<string>()
    const promises = refs.map((ref: { act: string; section: string }) =>
      api.cases(ref.act, ref.section).catch(() => ({ cases: [] }))
    )
    Promise.all(promises).then((results) => {
      const all: RelatedCase[] = []
      for (const result of results) {
        const casesList = result.cases || []
        for (const c of casesList) {
          if (!seen.has(c.citation)) {
            seen.add(c.citation)
            all.push({ citation: c.citation, title: c.title, court: c.court, year: c.year })
          }
        }
      }
      setRelatedCases(all)
      setRelatedLoading(false)
    })
  }, [rulingData])

  return (
    <div>
      <div style={{
        marginBottom: 20, color: COLORS.textMuted, fontSize: 12,
        fontFamily: "'Montserrat', sans-serif", letterSpacing: 0.3,
        textTransform: 'uppercase' as const,
      }}>
        Ruling &rsaquo; {rulingData.citation}
      </div>
      <h1 style={{
        color: COLORS.heading, fontSize: isMobile ? 20 : 22, marginBottom: 16,
        fontWeight: 600, borderBottom: `1px solid ${COLORS.border}`, paddingBottom: 8,
      }}>
        {fm.title || rulingData.citation}{descriptiveTitle ? ` — ${descriptiveTitle}` : ''}
        <a
          href={`/api/ruling/${encodeURIComponent(rulingData.citation)}/download`}
          style={{
            fontSize: 12, fontWeight: 400, marginLeft: 12,
            color: COLORS.accent, textDecoration: 'none',
          }}
          title="Download raw text"
        >
          (download)
        </a>
      </h1>

      {/* Summary collapsible section */}
      <div style={{
        marginBottom: 20, border: `1px solid ${COLORS.border}`,
        borderRadius: 6, overflow: 'hidden',
      }}>
        <button
          onClick={() => setSummaryOpen(!summaryOpen)}
          style={{
            width: '100%', padding: '10px 14px',
            background: COLORS.surface, border: 'none',
            cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', color: COLORS.heading,
            fontWeight: 600, fontSize: 13,
            fontFamily: "'Montserrat', sans-serif",
          }}
        >
          <span>Summary</span>
          <span style={{ transform: summaryOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}>
            ▼
          </span>
        </button>
        {summaryOpen && (
          <div style={{
            padding: '12px 14px', fontSize: 13, color: COLORS.textMuted,
            fontFamily: "'Montserrat', sans-serif", lineHeight: 1.6,
            background: COLORS.bg,
          }}>
            AI-powered summary coming soon.
          </div>
        )}
      </div>

      {/* Table of Contents — only when ## headers exist */}
      {toc.length > 0 && (
        <div style={{
          marginBottom: 24, padding: 16, background: COLORS.surface,
          borderRadius: 6, border: `1px solid ${COLORS.border}`,
        }}>
          <h3 style={{
            margin: 0, marginBottom: 10, color: COLORS.heading, fontSize: 14,
            fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
          }}>
            Contents
          </h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {toc.map((item) => (
              <li
                key={item.id}
                style={{
                  paddingLeft: item.level === 3 ? 16 : 0,
                  marginBottom: 4,
                }}
              >
                <a
                  href={`#${item.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    const el = document.getElementById(item.id)
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }}
                  style={{
                    color: COLORS.accent,
                    textDecoration: 'none',
                    fontSize: 13,
                    fontFamily: "'Montserrat', sans-serif",
                  }}
                >
                  {item.text}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ruling body */}
      <div style={{ lineHeight: 1.7, fontSize: isMobile ? 15 : 15, color: COLORS.text }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={components}>
          {body}
        </ReactMarkdown>
      </div>

      {/* Referenced Sections */}
      {rulingData.referenced_sections?.length > 0 && (
        <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, marginBottom: 16, fontWeight: 600 }}>
            Referenced Sections
          </h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {rulingData.referenced_sections.map((ref: { act: string; section: string; title?: string }) => (
              <li key={`${ref.act}-${ref.section}`} style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                <a
                  href={`/${ref.act}/s${ref.section}`}
                  onClick={(e) => {
                    e.preventDefault()
                    onNavigate(ref.act, ref.section)
                  }}
                  style={{ color: COLORS.accent, textDecoration: 'none', fontSize: 14 }}
                >
                  {shortActName(ref.act)} s{ref.section} {ref.title && `— ${ref.title}`}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Related Cases */}
      {relatedCases.length > 0 && (
        <div style={{ marginTop: 32, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, marginBottom: 16, fontWeight: 600 }}>
            Related Cases <span style={{ color: COLORS.textMuted, fontSize: 13, fontWeight: 400 }}>({relatedCases.length})</span>
          </h2>
          {relatedLoading ? (
            <p style={{ color: COLORS.textMuted, fontSize: 13 }}>Loading...</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {relatedCases.map((c) => (
                <li key={c.citation} style={{ marginBottom: 8 }}>
                  <a
                    href={`/tax-cases/case/${encodeURIComponent(c.citation)}`}
                    onClick={(e) => {
                      e.preventDefault()
                      onNavigateRuling(c.citation)
                    }}
                    style={{ color: COLORS.accent, textDecoration: 'none', fontSize: 14 }}
                  >
                    {c.title || c.citation}
                  </a>
                  {c.year && (
                    <span style={{ color: COLORS.textMuted, fontSize: 12, marginLeft: 6 }}>
                      ({c.year})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}