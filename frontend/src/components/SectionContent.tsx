import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { COLORS } from './common/types'
import { createMarkdownComponents } from './MarkdownRenderers'
import SmartLinkPanel from './SmartLinkPanel'
import { api } from '../api'

// Helper: count badge
function Badge({ count, label }: { count: number; label: string }) {
  if (count === 0) return null
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: 10,
      background: COLORS.surfaceHover, color: COLORS.textMuted,
      fontSize: 11, fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
      whiteSpace: 'nowrap',
    }}>
      {label} {count}
    </span>
  )
}

// Helper: collapsible group within References
function RefGroup({
  title, open, setOpen, children,
}: {
  title: string; open: boolean; setOpen: (v: boolean) => void; children: React.ReactNode
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
        <span>{title}</span>
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

type SectionContentProps = {
  act: string
  sectionData: any
  commentaryData: any
  casesData: any
  rulingsForSectionData: any
  isMobile: boolean
  isPinned: boolean
  togglePin: () => void
  renderLink?: (href?: string, children?: React.ReactNode) => React.ReactNode | null
  onNavigate: (act: string, section: string, anchor?: string) => void
  onNavigateRuling: (citation: string) => void
  commentaryOpen: boolean
  setCommentaryOpen: (v: boolean) => void
  casesOpen: boolean
  setCasesOpen: (v: boolean) => void
  rulingsOpen: boolean
  setRulingsOpen: (v: boolean) => void
}

export default function SectionContent({
  act,
  sectionData,
  commentaryData,
  casesData,
  rulingsForSectionData,
  isMobile,
  isPinned,
  togglePin,
  renderLink,
  onNavigate,
  onNavigateRuling,
  commentaryOpen,
  setCommentaryOpen,
  casesOpen,
  setCasesOpen,
  rulingsOpen,
  setRulingsOpen,
}: SectionContentProps) {
  const fm = sectionData?.frontmatter || {}
  const components = createMarkdownComponents(isMobile, act, onNavigate, onNavigateRuling, renderLink)

  // Comments state
  const [comments, setComments] = useState<any[]>([])
  const [commentsOpen, setCommentsOpen] = useState(false)
  const [commentAuthor, setCommentAuthor] = useState('')
  const [commentText, setCommentText] = useState('')
  const [commentLoading, setCommentLoading] = useState(false)

  // Cross-reference state
  const [sectionRefsData, setSectionRefsData] = useState<any>(null)
  const [refsOpen, setRefsOpen] = useState(false)
  const [refsCasesOpen, setRefsCasesOpen] = useState(false)
  const [refsRulingsOpen, setRefsRulingsOpen] = useState(false)
  const [refsSectionsOpen, setRefsSectionsOpen] = useState(false)
  const [refsDefinitionsOpen, setRefsDefinitionsOpen] = useState(false)

  const sectionId = fm.section || ''

  useEffect(() => {
    if (!act || !sectionId) {
      setComments([])
      return
    }
    api.listComments(act, sectionId)
      .then(data => setComments(data.comments || []))
      .catch(() => setComments([]))
  }, [act, sectionId])

  useEffect(() => {
    if (!act || !sectionId) return
    api.sectionRefs(act, sectionId)
      .then(data => setSectionRefsData(data))
      .catch(() => setSectionRefsData(null))
  }, [act, sectionId])

  const handleAddComment = async () => {
    if (!commentText.trim()) return
    setCommentLoading(true)
    try {
      const newComment = await api.createComment(act, sectionId, commentAuthor || 'Anonymous', commentText)
      setComments(prev => [newComment, ...prev])
      setCommentText('')
      setCommentAuthor('')
    } catch (e) {
      alert('Failed to add comment')
    } finally {
      setCommentLoading(false)
    }
  }

  const handleResolve = async (id: number) => {
    try {
      await api.resolveComment(id)
      setComments(prev => prev.map(c => c.id === id ? { ...c, resolved: true } : c))
    } catch (e) {
      alert('Failed to resolve comment')
    } finally {
      // No longer need setCommentLoading(false) here, it's for addComment
    }
  }

  return (
    <div>
      <div style={{
        marginBottom: 20, color: COLORS.textMuted, fontSize: 12,
        fontFamily: "'Montserrat', sans-serif", letterSpacing: 0.3,
        textTransform: 'uppercase' as const, display: 'flex', alignItems: 'center',
      }}>
        {fm.act} &rsaquo; Part {fm.part} &rsaquo; Division {fm.division}
        <button
          onClick={togglePin}
          style={{
            marginLeft: 12, padding: '4px 8px', borderRadius: 4,
            background: isPinned ? COLORS.accent : COLORS.surface,
            color: isPinned ? '#fff' : COLORS.textMuted,
            border: `1px solid ${COLORS.border}`, fontSize: 11, cursor: 'pointer',
            fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
            whiteSpace: 'nowrap',
            alignSelf: 'flex-start',
          }}
        >
          {isPinned ? 'Unpin' : 'Pin'}
        </button>
      </div>

      <div style={{ lineHeight: 1.7, fontSize: isMobile ? 15 : 15, color: COLORS.text }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={components}>
          {sectionData.body || sectionData.markdown}
        </ReactMarkdown>
      </div>

      {/* Cross-Reference Map — aggregated references with count badges */}
      <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: 12 }}
          onClick={() => setRefsOpen(!refsOpen)}
        >
          <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, fontWeight: 600, margin: 0 }}>
            References
          </h2>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Badge count={(casesData?.cases || casesData || []).length} label="Cases" />
            <Badge count={(rulingsForSectionData?.rulings || []).length} label="Rulings" />
            <Badge count={(sectionRefsData?.sections || []).length + (sectionRefsData?.cross_act_sections || []).length} label="Sections" />
            <Badge count={(sectionRefsData?.definitions || []).length} label="Defs" />
            <span style={{ color: COLORS.textMuted, fontSize: 20 }}>{refsOpen ? '\u25b2' : '\u25bc'}</span>
          </div>
        </div>
        {refsOpen && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {/* Cases — grouped by court */}
            {(casesData?.cases || casesData || []).length > 0 && (
              <RefGroup
                title={`Cases (${(casesData?.cases || casesData || []).length})`}
                open={refsCasesOpen}
                setOpen={setRefsCasesOpen}
              >
                {(() => {
                  const allCases = casesData?.cases || casesData || []
                  const groups: Record<string, any[]> = {}
                  const courtOrder = ['HCA', 'FCAFC', 'FCA', 'AATA', 'ARTA']
                  for (const c of allCases) {
                    const court = c.court || 'Other'
                    if (!groups[court]) groups[court] = []
                    groups[court].push(c)
                  }
                  return courtOrder.map(court =>
                    groups[court]?.length ? (
                      <div key={court} style={{ marginBottom: 8 }}>
                        <div style={{
                          fontSize: 11, fontWeight: 600, color: COLORS.textMuted,
                          fontFamily: "'Montserrat', sans-serif", textTransform: 'uppercase',
                          letterSpacing: '0.5px', marginBottom: 4, padding: '0 10px',
                        }}>
                          {court === 'HCA' ? 'High Court' : court === 'FCAFC' ? 'Full Federal Court' : court === 'FCA' ? 'Federal Court' : court === 'AATA' ? 'AAT' : court === 'ARTA' ? 'ART' : court} ({groups[court].length})
                        </div>
                        {groups[court].map((c: any, i: number) => (
                          <div
                            key={c.citation || i}
                            style={{
                              padding: '6px 10px', borderRadius: 4, fontSize: 13,
                              background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                              cursor: 'pointer', color: COLORS.accent, marginBottom: 2,
                            }}
                            onClick={() => onNavigate('tax-cases', c.citation)}
                            onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                            onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                          >
                            <strong>{c.citation}</strong>{c.title ? ` — ${c.title}` : ''}
                          </div>
                        ))}
                      </div>
                    ) : null
                  )
                })()}
              </RefGroup>
            )}

            {/* Rulings */}
            {(rulingsForSectionData?.rulings || []).length > 0 && (
              <RefGroup
                title={`Rulings (${(rulingsForSectionData?.rulings || []).length})`}
                open={refsRulingsOpen}
                setOpen={setRefsRulingsOpen}
              >
                {(rulingsForSectionData?.rulings || []).map((r: any, i: number) => (
                  <div
                    key={r.citation || i}
                    style={{
                      padding: '6px 10px', borderRadius: 4, fontSize: 13,
                      background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      cursor: 'pointer', color: COLORS.accent,
                    }}
                    onClick={() => onNavigateRuling?.(r.citation)}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                  >
                    {r.title || r.citation_display || r.citation}
                  </div>
                ))}
              </RefGroup>
            )}

            {/* Sections referencing this section */}
            {((sectionRefsData?.sections || []).length > 0 || (sectionRefsData?.cross_act_sections || []).length > 0) && (
              <RefGroup
                title={`Sections (${(sectionRefsData?.sections || []).length + (sectionRefsData?.cross_act_sections || []).length})`}
                open={refsSectionsOpen}
                setOpen={setRefsSectionsOpen}
              >
                {(sectionRefsData?.sections || []).length > 0 && (
                  <>
                    <div style={{ color: COLORS.textMuted, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6, marginTop: 4 }}>
                      Same Act
                    </div>
                    {(sectionRefsData?.sections || []).map((s: any, i: number) => (
                      <div
                        key={`s-${i}`}
                        style={{
                          padding: '6px 10px', borderRadius: 4, fontSize: 13,
                          background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                          cursor: 'pointer', color: COLORS.accent,
                        }}
                        onClick={() => onNavigate(act, s.section)}
                        onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                        onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                      >
                        s{s.section}{s.title ? ` — ${s.title}` : ''}
                      </div>
                    ))}
                  </>
                )}
                {(sectionRefsData?.cross_act_sections || []).length > 0 && (
                  <>
                    <div style={{ color: COLORS.textMuted, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6, marginTop: 8 }}>
                      Cross-Act
                    </div>
                    {(sectionRefsData?.cross_act_sections || []).map((s: any, i: number) => (
                      <div
                        key={`ca-${i}`}
                        style={{
                          padding: '6px 10px', borderRadius: 4, fontSize: 13,
                          background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                          cursor: 'pointer', color: COLORS.accent,
                        }}
                        onClick={() => onNavigate(s.act, s.section)}
                        onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                        onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                      >
                        {s.act} s{s.section}{s.title ? ` — ${s.title}` : ''}
                      </div>
                    ))}
                  </>
                )}
              </RefGroup>
            )}

            {/* Definitions */}
            {(sectionRefsData?.definitions || []).length > 0 && (
              <RefGroup
                title={`Definitions (${(sectionRefsData?.definitions || []).length})`}
                open={refsDefinitionsOpen}
                setOpen={setRefsDefinitionsOpen}
              >
                {(sectionRefsData?.definitions || []).map((d: any, i: number) => (
                  <div
                    key={d.term || i}
                    style={{
                      padding: '6px 10px', borderRadius: 4, fontSize: 13,
                      background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                      cursor: 'pointer', color: COLORS.accent,
                    }}
                    onClick={() => onNavigate(act, d.section)}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surfaceHover }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = COLORS.surface }}
                  >
                    <span style={{ fontWeight: 500, color: COLORS.text }}>{d.term}</span>
                    {' — '}
                    <span style={{ color: COLORS.textMuted }}>defined in s{d.section}</span>
                  </div>
                ))}
              </RefGroup>
            )}
          </div>
        )}
      </div>

      {/* Comments */}
      <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: 12 }}
             onClick={() => setCommentsOpen(!commentsOpen)}>
          <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, fontWeight: 600, margin: 0 }}>
            Comments {comments.length > 0 && `(${comments.length})`}
          </h2>
          <span style={{ color: COLORS.textMuted, fontSize: 20 }}>{commentsOpen ? '\u25b2' : '\u25bc'}</span>
        </div>
        {commentsOpen && (
          <div>
            {/* Add comment form */}
            <div style={{ marginBottom: 16, padding: 12, background: COLORS.surface, borderRadius: 6, border: `1px solid ${COLORS.border}` }}>
              <input
                value={commentAuthor}
                onChange={e => setCommentAuthor(e.target.value)}
                placeholder="Your name (optional)"
                style={{
                  width: '100%', padding: 8, marginBottom: 8, borderRadius: 4,
                  background: COLORS.bg, color: COLORS.heading,
                  border: `1px solid ${COLORS.border}`, fontSize: 13,
                  fontFamily: "'Montserrat', sans-serif",
                }}
              />
              <textarea
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Add a comment..."
                rows={3}
                style={{
                  width: '100%', padding: 8, marginBottom: 8, borderRadius: 4,
                  background: COLORS.bg, color: COLORS.heading,
                  border: `1px solid ${COLORS.border}`, fontSize: 13,
                  fontFamily: "'Montserrat', sans-serif",
                  resize: 'vertical',
                }}
              />
              <button
                onClick={handleAddComment}
                disabled={commentLoading || !commentText.trim()}
                style={{
                  padding: '8px 16px', borderRadius: 4,
                  background: commentLoading || !commentText.trim() ? COLORS.surfaceHover : COLORS.accent,
                  color: '#fff', border: 'none', fontSize: 13, cursor: commentLoading || !commentText.trim() ? 'not-allowed' : 'pointer',
                  fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
                }}
              >
                {commentLoading ? 'Posting...' : 'Post Comment'}
              </button>
            </div>

            {/* Comments list */}
            {comments.length === 0 ? (
              <p style={{ color: COLORS.textMuted, fontSize: 13 }}>No comments yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {comments.map((c: any) => (
                  <div key={c.id} style={{
                    padding: 12, background: COLORS.surface, borderRadius: 6,
                    border: `1px solid ${COLORS.border}`, opacity: c.resolved ? 0.5 : 1,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, color: COLORS.heading, fontSize: 13 }}>{c.author}</span>
                      <span style={{ color: COLORS.textMuted, fontSize: 11 }}>
                        {new Date(c.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p style={{ margin: 0, color: COLORS.text, fontSize: 14, lineHeight: 1.6 }}>{c.text}</p>
                    {!c.resolved && (
                      <button
                        onClick={() => handleResolve(c.id)}
                        style={{
                          marginTop: 8, padding: '4px 10px', borderRadius: 4,
                          background: COLORS.surfaceHover, color: COLORS.textMuted,
                          border: `1px solid ${COLORS.border}`, fontSize: 11, cursor: 'pointer',
                          fontFamily: "'Montserrat', sans-serif",
                        }}
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Smart Links — Related content */}
      <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
        <SmartLinkPanel
          act={act}
          section={sectionId}
          onNavigate={onNavigate}
          onNavigateRuling={onNavigateRuling}
          rulingsForSection={rulingsForSectionData?.rulings || []}
        />
      </div>
    </div>
  )
}
