import React, { useEffect, useState } from 'react'
import { COLORS } from './common/types'

const API = ''

interface Issue {
  ticket: string
  category: string
  tool: string | null
  note: string | null
  status: string
  hits: number
  created: string | null
  expected: string | null
  actual: string | null
  fixed: string | null
}

export default function IssuesModal({ onClose }: { onClose: () => void }) {
  const [issues, setIssues] = useState<Issue[]>([])
  const [loading, setLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)
  const [reportText, setReportText] = useState('')
  const [reportSent, setReportSent] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/issues`).then(r => r.json()).then(d => {
      setIssues(d.issues || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const openIssues = issues.filter(i => i.status === 'open' || i.status === 'known')
  const fixedIssues = issues.filter(i => i.status === 'fixed' || i.status === 'resolved')

  const handleSubmit = async () => {
    if (!reportText.trim()) return
    try {
      const r = await fetch(`${API}/api/issues`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: reportText.trim(), category: 'bug' }),
      })
      const data = await r.json()
      if (data.ticket) {
        setReportSent(true)
        // Refresh
        const refreshed = await fetch(`${API}/api/issues`).then(r => r.json())
        setIssues(refreshed.issues || [])
      }
    } catch {}
  }

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 10000,
      background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: COLORS?.surface || '#1a1a2e', borderRadius: 12,
        width: '90%', maxWidth: 600, maxHeight: '80vh',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '16px 20px', borderBottom: `1px solid ${COLORS?.border || '#333'}`,
        }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: COLORS?.heading || '#fff', fontFamily: "'Montserrat', sans-serif" }}>
            Issues & Bug Reports
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: COLORS?.textMuted || '#888',
            cursor: 'pointer', fontSize: 20, lineHeight: 1, padding: '4px 8px',
          }}>✕</button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px' }}>
          {/* Report a bug form */}
          <div style={{
            marginBottom: 16, padding: 12,
            background: COLORS?.bg || '#0e0e1e', borderRadius: 8,
            border: `1px solid ${COLORS?.border || '#333'}`,
          }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: COLORS?.heading || '#fff', marginBottom: 8 }}>
              {reportSent ? '✓ Report submitted' : 'Report a bug'}
            </div>
            {!reportSent && (
              <>
                <textarea
                  value={reportText}
                  onChange={e => setReportText(e.target.value)}
                  placeholder="Describe what went wrong..."
                  rows={3}
                  style={{
                    width: '100%', padding: 8, borderRadius: 6,
                    background: COLORS?.surface || '#1a1a2e', color: COLORS?.heading || '#fff',
                    border: `1px solid ${COLORS?.border || '#333'}`, fontSize: 12,
                    fontFamily: "'Montserrat', sans-serif", resize: 'vertical',
                    outline: 'none', boxSizing: 'border-box',
                  }}
                />
                <button
                  onClick={handleSubmit}
                  disabled={!reportText.trim()}
                  style={{
                    marginTop: 8, padding: '6px 14px', borderRadius: 6,
                    background: reportText.trim() ? (COLORS?.accent || '#279e88') : (COLORS?.border || '#555'),
                    color: reportText.trim() ? '#fff' : (COLORS?.textMuted || '#888'),
                    border: 'none', cursor: reportText.trim() ? 'pointer' : 'default',
                    fontSize: 11, fontWeight: 600,
                    fontFamily: "'Montserrat', sans-serif",
                  }}
                >
                  Submit
                </button>
              </>
            )}
          </div>

          {/* Open / Known issues */}
          <div style={{ fontSize: 12, fontWeight: 600, color: COLORS?.heading || '#fff', marginBottom: 8 }}>
            Open Issues ({openIssues.length})
          </div>
          {loading && <div style={{ fontSize: 11, color: COLORS?.textMuted || '#888' }}>Loading...</div>}
          {!loading && openIssues.length === 0 && (
            <div style={{ fontSize: 11, color: COLORS?.textMuted || '#888', marginBottom: 16 }}>No open issues.</div>
          )}
          {openIssues.map(issue => (
            <div key={issue.ticket} style={{
              padding: '8px 10px', marginBottom: 6,
              background: COLORS?.bg || '#0e0e1e', borderRadius: 6,
              border: `1px solid ${COLORS?.border || '#333'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#e67e22' }}>
                  {issue.ticket}
                  <span style={{ color: COLORS?.textMuted || '#888', fontWeight: 400 }}>
                    {' '}· {issue.category}{issue.tool ? ` · ${issue.tool}` : ''}
                  </span>
                </span>
                <span style={{ fontSize: 10, color: COLORS?.textMuted || '#888' }}>
                  {issue.hits > 0 ? `${issue.hits} hit${issue.hits > 1 ? 's' : ''}` : ''}
                  {issue.created ? ` · ${new Date(issue.created).toLocaleDateString()}` : ''}
                </span>
              </div>
              {issue.note && (
                <div style={{ fontSize: 11, color: COLORS?.textMuted || '#aaa', lineHeight: 1.4 }}>
                  {issue.note}
                </div>
              )}
            </div>
          ))}

          {/* Resolved issues — collapsible */}
          {fixedIssues.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <button
                onClick={() => setShowResolved(!showResolved)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: COLORS?.textMuted || '#888', fontSize: 11,
                  fontFamily: "'Montserrat', sans-serif",
                  display: 'flex', alignItems: 'center', gap: 4, padding: 0,
                }}
              >
                {showResolved ? '▼' : '▶'} Resolved ({fixedIssues.length})
              </button>
              {showResolved && fixedIssues.map(issue => (
                <div key={issue.ticket} style={{
                  padding: '6px 10px', marginTop: 4,
                  background: COLORS?.bg || '#0e0e1e', borderRadius: 6,
                  border: `1px solid ${COLORS?.border || '#333'}`,
                  opacity: 0.7,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#4caf50' }}>
                      {issue.ticket} <span style={{ fontWeight: 400, color: COLORS?.textMuted || '#888' }}>· {issue.category}</span>
                    </span>
                    <span style={{ fontSize: 10, color: COLORS?.textMuted || '#888' }}>
                      {issue.created ? new Date(issue.created).toLocaleDateString() : ''}
                    </span>
                  </div>
                  {issue.note && (
                    <div style={{ fontSize: 11, color: COLORS?.textMuted || '#aaa', marginTop: 2, lineHeight: 1.3 }}>
                      {issue.note}
                    </div>
                  )}
                  {issue.fixed && (
                    <div style={{ fontSize: 11, color: '#4caf50', marginTop: 2, lineHeight: 1.3 }}>
                      Fix: {issue.fixed}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}