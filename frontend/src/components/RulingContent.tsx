import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { COLORS } from './common/types'
import { createMarkdownComponents } from './MarkdownRenderers'

type RulingContentProps = {
  rulingData: any
  isMobile: boolean
  renderLink?: (href?: string, children?: React.ReactNode) => React.ReactNode | null
  onNavigate: (act: string, section: string, anchor?: string) => void
  onNavigateRuling: (citation: string) => void
}

export default function RulingContent({
  rulingData,
  isMobile,
  renderLink,
  onNavigate,
  onNavigateRuling,
}: RulingContentProps) {
  const fm = rulingData?.frontmatter || {}
  const components = createMarkdownComponents(isMobile, 'rulings', onNavigate, onNavigateRuling, renderLink)

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
        {fm.title}
      </h1>
      <div style={{ lineHeight: 1.7, fontSize: isMobile ? 15 : 15, color: COLORS.text }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={components}>
          {rulingData.body}
        </ReactMarkdown>
      </div>
      {rulingData.referenced_sections?.length > 0 && (
        <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, marginBottom: 16, fontWeight: 600 }}>
            Referenced Sections
          </h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {rulingData.referenced_sections.map((ref: { act: string; section: string; title?: string }) => (
              <li key={`${ref.act}-${ref.section}`} style={{ marginBottom: 8 }}>
                <a
                  href={`/${ref.act}/s${ref.section}`}
                  onClick={(e) => {
                    e.preventDefault()
                    onNavigate(ref.act, ref.section)
                  }}
                  style={{ color: COLORS.accent, textDecoration: 'none', fontSize: 14 }}
                >
                  {ref.section} {ref.title && `— ${ref.title}`}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
