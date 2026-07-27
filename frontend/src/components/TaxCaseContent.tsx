import React from 'react'
import { COLORS } from './common/types'

type TaxCaseContentProps = {
  caseData: any
  isMobile: boolean
}

export default function TaxCaseContent({ caseData, isMobile }: TaxCaseContentProps) {
  if (!caseData) return null

  const {
    citation,
    title,
    court,
    court_label,
    decision_date,
    judges,
    outcome,
    catchwords,
    head_notes,
    related_provisions,
    related_rulings,
    paragraph_count,
    content_length,
    cited_by_count,
    legislation_refs,
    austlii_url,
    hca_url,
    fedcourt_url,
  } = caseData

  return (
    <div>
      <div style={{
        marginBottom: 20, color: COLORS.textMuted, fontSize: 12,
        fontFamily: "'Montserrat', sans-serif", letterSpacing: 0.3,
        textTransform: 'uppercase' as const,
      }}>
        Tax Case &rsaquo; {citation}
      </div>
      <h1 style={{
        color: COLORS.heading, fontSize: isMobile ? 20 : 22, marginBottom: 16,
        fontWeight: 600, borderBottom: `1px solid ${COLORS.border}`, paddingBottom: 8,
      }}>
        {title || citation}
      </h1>

      {/* Metadata table */}
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 8,
        marginBottom: 24, fontSize: isMobile ? 13 : 14,
        fontFamily: "'Montserrat', sans-serif",
      }}>
        {citation && (
          <MetadataRow label="Citation" value={citation} />
        )}
        {court_label && (
          <MetadataRow label="Court" value={court_label} />
        )}
        {court && (
          <MetadataRow label="Court Key" value={court} />
        )}
        {decision_date && (
          <MetadataRow label="Decision Date" value={decision_date} />
        )}
        {judges && (
          <MetadataRow label="Judges" value={Array.isArray(judges) ? judges.join(', ') : judges} />
        )}
        {outcome && (
          <MetadataRow label="Outcome" value={outcome} />
        )}
        {catchwords && (
          <MetadataRow label="Catchwords" value={catchwords} />
        )}
        {paragraph_count !== undefined && paragraph_count !== null && (
          <MetadataRow label="Paragraphs" value={String(paragraph_count)} />
        )}
        {content_length !== undefined && content_length !== null && (
          <MetadataRow label="Content Length" value={`${(content_length / 1024).toFixed(1)} KB`} />
        )}
        {cited_by_count !== undefined && cited_by_count !== null && (
          <MetadataRow label="Cited By" value={String(cited_by_count)} />
        )}
      </div>

      {/* Links */}
      {(austlii_url || hca_url || fedcourt_url) && (
        <div style={{ marginBottom: 24, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {austlii_url && (
            <a
              href={austlii_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '8px 14px', borderRadius: 6,
                background: COLORS.accent, color: '#fff',
                textDecoration: 'none', fontSize: 12,
                fontFamily: "'Montserrat', sans-serif",
                fontWeight: 500,
              }}
            >
              View on AustLII &rarr;
            </a>
          )}
          {hca_url && (
            <a
              href={hca_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '8px 14px', borderRadius: 6,
                background: COLORS.surface, color: COLORS.accent,
                border: `1px solid ${COLORS.border}`,
                textDecoration: 'none', fontSize: 12,
                fontFamily: "'Montserrat', sans-serif",
                fontWeight: 500,
              }}
            >
              View on HCA &rarr;
            </a>
          )}
          {fedcourt_url && (
            <a
              href={fedcourt_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '8px 14px', borderRadius: 6,
                background: COLORS.surface, color: COLORS.accent,
                border: `1px solid ${COLORS.border}`,
                textDecoration: 'none', fontSize: 12,
                fontFamily: "'Montserrat', sans-serif",
                fontWeight: 500,
              }}
            >
              View on FedCourt &rarr;
            </a>
          )}
        </div>
      )}

      {/* Head notes */}
      {head_notes && (
        <div style={{ marginTop: 24 }}>
          <h2 style={{
            color: COLORS.heading, fontSize: isMobile ? 16 : 17,
            marginBottom: 12, fontWeight: 600,
            fontFamily: "'Montserrat', sans-serif",
          }}>
            Head Notes
          </h2>
          <div style={{ fontSize: isMobile ? 13 : 14, lineHeight: 1.7, color: COLORS.text }}>
            {typeof head_notes === 'object' ? (
              <pre style={{
                whiteSpace: 'pre-wrap', fontFamily: "'Lora', serif",
                fontSize: isMobile ? 13 : 14, color: COLORS.text,
                lineHeight: 1.7, margin: 0,
              }}>
                {JSON.stringify(head_notes, null, 2)}
              </pre>
            ) : (
              <div>{head_notes}</div>
            )}
          </div>
        </div>
      )}

      {/* Legislation refs */}
      {legislation_refs && legislation_refs.length > 0 && (
        <div style={{ marginTop: 32, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{
            color: COLORS.heading, fontSize: isMobile ? 16 : 17,
            marginBottom: 12, fontWeight: 600,
            fontFamily: "'Montserrat', sans-serif",
          }}>
            Legislation References
          </h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {legislation_refs.map((ref: any, i: number) => (
              <li key={i} style={{
                padding: '6px 10px', marginBottom: 4,
                background: COLORS.bg, borderRadius: 4,
                fontSize: 12, fontFamily: "'Montserrat', sans-serif",
                color: COLORS.text,
              }}>
                {ref.act && <span style={{ color: COLORS.accent }}>{ref.act}</span>}
                {ref.section && <span> s{ref.section}</span>}
                {ref.title && <span style={{ color: COLORS.textMuted }}> — {ref.title}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Related provisions */}
      {related_provisions && related_provisions.length > 0 && (
        <div style={{ marginTop: 24, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{
            color: COLORS.heading, fontSize: isMobile ? 16 : 17,
            marginBottom: 12, fontWeight: 600,
            fontFamily: "'Montserrat', sans-serif",
          }}>
            Related Provisions
          </h2>
          <div style={{ fontSize: isMobile ? 13 : 14, color: COLORS.text, lineHeight: 1.7 }}>
            {Array.isArray(related_provisions)
              ? related_provisions.join(', ')
              : related_provisions}
          </div>
        </div>
      )}

      {/* Related rulings */}
      {related_rulings && related_rulings.length > 0 && (
        <div style={{ marginTop: 24, borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
          <h2 style={{
            color: COLORS.heading, fontSize: isMobile ? 16 : 17,
            marginBottom: 12, fontWeight: 600,
            fontFamily: "'Montserrat', sans-serif",
          }}>
            Related Rulings
          </h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {related_rulings.map((ruling: string, i: number) => (
              <li key={i} style={{
                padding: '4px 0', fontSize: 12,
                fontFamily: "'Montserrat', sans-serif",
                color: COLORS.accent,
              }}>
                {ruling}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex', gap: 8,
      padding: '6px 10px',
      background: 'rgba(0,0,0,0.15)',
      borderRadius: 4,
    }}>
      <span style={{
        fontWeight: 600, color: COLORS.heading,
        minWidth: 130, flexShrink: 0,
        fontSize: 12,
      }}>
        {label}
      </span>
      <span style={{ color: COLORS.text, fontSize: 12 }}>
        {value}
      </span>
    </div>
  )
}
