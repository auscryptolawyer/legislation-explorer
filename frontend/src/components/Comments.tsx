import React, { useEffect, useState } from 'react';
import { COLORS } from './common/types';

type Comment = {
  id: number;
  author: string;
  text: string;
  created_at: string;
  resolved: boolean;
};

type CommentsProps = {
  act: string;
  section: string;
  isMobile: boolean;
};

export default function Comments({ act, section, isMobile }: CommentsProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [author, setAuthor] = useState('');
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showResolved, setShowResolved] = useState(false);

  const apiBase = '';

  const fetchComments = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${apiBase}/api/comments/${encodeURIComponent(act)}/${encodeURIComponent(section)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setComments(data.comments || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load comments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (act && section) {
      fetchComments();
    }
  }, [act, section]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`${apiBase}/api/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ act, section, author: author || 'Anonymous', text: text.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setText('');
      setAuthor('');
      fetchComments();
    } catch (e: any) {
      setError(e.message || 'Failed to post comment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (id: number) => {
    try {
      const res = await fetch(`${apiBase}/api/comments/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment_id: id }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      fetchComments();
    } catch (e: any) {
      setError(e.message || 'Failed to resolve');
    }
  };

  const filtered = showResolved ? comments : comments.filter((c) => !c.resolved);
  const unresolvedCount = comments.filter((c) => !c.resolved).length;

  return (
    <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.border}`, paddingTop: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ color: COLORS.heading, fontSize: isMobile ? 17 : 18, fontWeight: 600, margin: 0 }}>
          Comments
          {unresolvedCount > 0 && (
            <span style={{
              background: COLORS.accent,
              color: '#fff',
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 10,
              marginLeft: 8,
              fontWeight: 700,
            }}>
              {unresolvedCount}
            </span>
          )}
        </h2>
        <button
          onClick={() => setShowResolved((s) => !s)}
          style={{
            background: 'transparent',
            border: 'none',
            color: COLORS.textMuted,
            fontSize: 12,
            cursor: 'pointer',
            fontFamily: "'Montserrat', sans-serif",
          }}
        >
          {showResolved ? 'Hide resolved' : 'Show resolved'}
        </button>
      </div>

      {error && (
        <div style={{ color: '#e57373', fontSize: 13, marginBottom: 12 }}>{error}</div>
      )}

      <form onSubmit={handleSubmit} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            type="text"
            placeholder="Name (optional)"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              border: `1px solid ${COLORS.border}`,
              background: COLORS.surface,
              color: COLORS.text,
              fontSize: 14,
              fontFamily: "'Lora', serif",
            }}
          />
        </div>
        <textarea
          placeholder="Log a bug or display issue..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: 6,
            border: `1px solid ${COLORS.border}`,
            background: COLORS.surface,
            color: COLORS.text,
            fontSize: 14,
            fontFamily: "'Lora', serif",
            resize: 'vertical',
            marginBottom: 8,
            boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={submitting || !text.trim()}
            style={{
              padding: '6px 16px',
              borderRadius: 6,
              background: COLORS.accent,
              color: '#fff',
              border: 'none',
              fontSize: 13,
              cursor: text.trim() ? 'pointer' : 'not-allowed',
              opacity: text.trim() ? 1 : 0.5,
              fontFamily: "'Montserrat', sans-serif",
              fontWeight: 500,
            }}
          >
            {submitting ? 'Posting...' : 'Post comment'}
          </button>
        </div>
      </form>

      {loading && comments.length === 0 ? (
        <div style={{ color: COLORS.textMuted, fontSize: 13 }}>Loading comments...</div>
      ) : filtered.length === 0 ? (
        <div style={{ color: COLORS.textMuted, fontSize: 13 }}>
          {showResolved ? 'No comments yet.' : 'No open issues. Great!'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filtered.map((c) => (
            <div
              key={c.id}
              style={{
                padding: '12px 14px',
                borderRadius: 6,
                background: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                opacity: c.resolved ? 0.6 : 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: COLORS.heading, fontSize: 13, fontWeight: 600 }}>
                    {c.author}
                  </span>
                  <span style={{ color: COLORS.textMuted, fontSize: 11 }}>
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  {c.resolved && (
                    <span style={{
                      color: COLORS.accent,
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: 0.3,
                    }}>
                      Resolved
                    </span>
                  )}
                </div>
                {!c.resolved && (
                  <button
                    onClick={() => handleResolve(c.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: COLORS.textMuted,
                      fontSize: 11,
                      cursor: 'pointer',
                      fontFamily: "'Montserrat', sans-serif",
                    }}
                    title="Mark as resolved"
                  >
                    Resolve
                  </button>
                )}
              </div>
              <div style={{ color: COLORS.text, fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {c.text}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
