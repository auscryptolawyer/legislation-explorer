import React, { useState, useEffect } from 'react';
import { COLORS } from './common/types';
import { api } from '../api';

interface MCPModalProps {
  open: boolean;
  onClose: () => void;
}

type TokenInfo = {
  id: number;
  created_at: number;
  last_used: number | null;
  request_count: number;
};

const MCPModal: React.FC<MCPModalProps> = ({ open, onClose }) => {
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  const baseUrl = 'https://legislation.scriptkitty.yachts/mcp/sse';
  const fullUrl = generatedToken ? `${baseUrl}?token=${generatedToken}` : baseUrl;

  useEffect(() => {
    if (open) {
      loadTokens();
      setGeneratedToken(null);
      setError(null);
    }
  }, [open]);

  const loadTokens = async () => {
    try {
      const data = await api.listMcpTokens();
      setTokens(data.tokens || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const generateToken = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.generateMcpToken();
      setGeneratedToken(data.token);
      loadTokens();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: 'url' | 'token') => {
    navigator.clipboard.writeText(text).then(() => {
      if (type === 'url') {
        setCopiedUrl(true);
        setTimeout(() => setCopiedUrl(false), 2000);
      } else {
        setCopiedToken(true);
        setTimeout(() => setCopiedToken(false), 2000);
      }
    }).catch(err => {
      console.error('Failed to copy: ', err);
    });
  };

  const formatDate = (ts: number | null) => {
    if (!ts) return 'Never';
    return new Date(ts * 1000).toLocaleString();
  };

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: COLORS.surface, border: `1px solid ${COLORS.border}`,
          borderRadius: 8, padding: 24, maxWidth: 600, width: '90%',
          overflowY: 'auto', maxHeight: '90vh', position: 'relative',
        }}
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'transparent', border: 'none',
            color: COLORS.textMuted, fontSize: 24, cursor: 'pointer',
            lineHeight: 1,
          }}
        >
          &times;
        </button>

        <h2 style={{ color: COLORS.heading, marginTop: 0, fontFamily: "'Montserrat', sans-serif", fontSize: 18 }}>
          MCP Server Connection
        </h2>

        <p style={{ color: COLORS.textMuted, fontSize: 13, lineHeight: 1.5 }}>
          Connect Claude Desktop or other MCP clients to this Legislation Explorer.
        </p>

        {/* Generate Token */}
        <div style={{ marginTop: 20 }}>
          <button
            onClick={generateToken}
            disabled={loading}
            style={{
              padding: '10px 18px', borderRadius: 6,
              background: COLORS.accent, color: '#fff',
              border: 'none', fontSize: 14, cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Generating...' : 'Generate New Token'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 12, color: '#ef4444', fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Newly generated token */}
        {generatedToken && (
          <div style={{
            marginTop: 20, padding: 16, borderRadius: 6,
            background: 'rgba(39,158,136,0.08)', border: `1px solid ${COLORS.accent}`,
          }}>
            <div style={{ color: COLORS.accent, fontSize: 12, fontWeight: 600, marginBottom: 8, fontFamily: "'Montserrat', sans-serif" }}>
              Copy this token now — it will not be shown again
            </div>
            <div style={{ position: 'relative' }}>
              <pre style={{
                background: COLORS.bg, color: COLORS.text,
                padding: 12, borderRadius: 6, fontSize: 12,
                overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                fontFamily: 'monospace', margin: 0,
                border: `1px solid ${COLORS.border}`,
              }}>
                {generatedToken}
              </pre>
              <button
                onClick={() => copyToClipboard(generatedToken, 'token')}
                style={{
                  position: 'absolute', top: 8, right: 8,
                  padding: '4px 10px', borderRadius: 4,
                  background: copiedToken ? COLORS.accent : COLORS.surface,
                  color: copiedToken ? '#fff' : COLORS.text,
                  border: `1px solid ${COLORS.border}`, fontSize: 11, cursor: 'pointer',
                  fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
                }}
              >
                {copiedToken ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
        )}

        {/* SSE URL */}
        <div style={{ marginTop: 24 }}>
          <div style={{ color: COLORS.heading, fontSize: 13, fontWeight: 600, marginBottom: 8, fontFamily: "'Montserrat', sans-serif" }}>
            SSE Endpoint URL
          </div>
          <div style={{ position: 'relative' }}>
            <pre style={{
              background: COLORS.bg, color: COLORS.text,
              padding: 14, borderRadius: 6, fontSize: 12,
              overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              fontFamily: 'monospace', margin: 0,
              border: `1px solid ${COLORS.border}`,
              minHeight: 40,
              display: 'flex', alignItems: 'center',
            }}>
              {fullUrl}
            </pre>
            <button
              onClick={() => copyToClipboard(fullUrl, 'url')}
              style={{
                position: 'absolute', top: 8, right: 8,
                padding: '6px 12px', borderRadius: 4,
                background: copiedUrl ? COLORS.accent : COLORS.surface,
                color: copiedUrl ? '#fff' : COLORS.text,
                border: `1px solid ${COLORS.border}`, fontSize: 12, cursor: 'pointer',
                fontWeight: 600, fontFamily: "'Montserrat', sans-serif",
                transition: 'background 0.2s ease, color 0.2s ease',
              }}
            >
              {copiedUrl ? 'Copied!' : 'Copy URL'}
            </button>
          </div>
        </div>

        {/* Token list */}
        {tokens.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ color: COLORS.heading, fontSize: 13, fontWeight: 600, marginBottom: 8, fontFamily: "'Montserrat', sans-serif" }}>
              Active Tokens ({tokens.length})
            </div>
            <div style={{
              maxHeight: 200, overflowY: 'auto',
              border: `1px solid ${COLORS.border}`, borderRadius: 6,
            }}>
              {tokens.map(t => (
                <div key={t.id} style={{
                  padding: '10px 12px',
                  borderBottom: `1px solid ${COLORS.border}`,
                  fontSize: 12, color: COLORS.text,
                  fontFamily: "'Montserrat', sans-serif",
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: COLORS.textMuted }}>Token #{t.id}</span>
                    <span style={{ color: COLORS.accent }}>{t.request_count} requests</span>
                  </div>
                  <div style={{ color: COLORS.textMuted, fontSize: 11, marginTop: 4 }}>
                    Created: {formatDate(t.created_at)} · Last used: {formatDate(t.last_used)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <p style={{ color: COLORS.textMuted, fontSize: 12, margin: '20px 0 0 0', lineHeight: 1.4 }}>
          In Claude Desktop, go to <strong>Settings → Developer → Add MCP Server</strong> and paste the URL above.
        </p>
      </div>
    </div>
  );
};

export default MCPModal;
