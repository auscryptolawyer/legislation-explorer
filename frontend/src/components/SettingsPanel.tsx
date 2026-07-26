import React, { useState } from 'react'
import { useTheme, FONTS } from '../ThemeContext'
import { COLORS } from './common/types'

const ACCENT_PRESETS = [
  '#279e88', '#2563eb', '#7c3aed', '#059669',
  '#d97706', '#dc2626', '#e11d48', '#0891b2',
]

export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const {
    colors: c, theme, accentColor, headingFont, bodyFont,
    userPrefs, setTheme, setAccentColor,
    setHeadingFont, setBodyFont, setDisplayName, setDefaultAct,
    resetTheme, savePrefs,
  } = useTheme()

  const [tab, setTab] = useState<'profile' | 'appearance'>('profile')
  const [editingDisplayName, setEditingDisplayName] = useState(userPrefs?.display_name || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [acts, setActs] = useState<{ id: string; name: string }[]>([])

  React.useEffect(() => {
    fetch('/api/acts').then(r => r.ok ? r.json() : []).then(setActs).catch(() => {})
  }, [])

  const handleSaveDisplayName = async () => {
    setSaving(true)
    setDisplayName(editingDisplayName)
    await savePrefs({ display_name: editingDisplayName })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleThemeToggle = (t: string) => {
    setTheme(t)
    savePrefs({ theme: t } as any)
  }

  const handleAccent = (color: string) => {
    setAccentColor(color)
    savePrefs({ accent_color: color } as any)
  }

  const handleHeadingFont = (f: string) => {
    setHeadingFont(f)
    savePrefs({ heading_font: f } as any)
  }

  const handleBodyFont = (f: string) => {
    setBodyFont(f)
    savePrefs({ body_font: f } as any)
  }

  const handleReset = () => {
    resetTheme()
    fetch('/api/user/prefs/reset', { method: 'POST' }).catch(() => {})
  }

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
          background: c.surface, borderRadius: 12,
          padding: 24, width: '90%', maxWidth: 520,
          maxHeight: '85vh', overflow: 'auto',
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
          border: `1px solid ${c.border}`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ margin: 0, color: c.heading, fontSize: 16, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif", fontWeight: 600 }}>
            Settings
          </h2>
          <button onClick={onClose} style={{
            background: 'transparent', border: 'none',
            color: c.textMuted, fontSize: 22, cursor: 'pointer', lineHeight: 1, padding: '0 4px',
          }}>&times;</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: `1px solid ${c.border}` }}>
          <button
            onClick={() => setTab('profile')}
            style={{
              padding: '8px 16px', border: 'none', cursor: 'pointer',
              background: 'transparent', color: tab === 'profile' ? c.accent : c.textMuted,
              fontSize: 12, fontWeight: tab === 'profile' ? 600 : 400,
              fontFamily: "var(--heading-font, 'Montserrat'), sans-serif",
              borderBottom: tab === 'profile' ? `2px solid ${c.accent}` : '2px solid transparent',
            }}
          >Profile</button>
          <button
            onClick={() => setTab('appearance')}
            style={{
              padding: '8px 16px', border: 'none', cursor: 'pointer',
              background: 'transparent', color: tab === 'appearance' ? c.accent : c.textMuted,
              fontSize: 12, fontWeight: tab === 'appearance' ? 600 : 400,
              fontFamily: "var(--heading-font, 'Montserrat'), sans-serif",
              borderBottom: tab === 'appearance' ? `2px solid ${c.accent}` : '2px solid transparent',
            }}
          >Appearance</button>
        </div>

        {tab === 'profile' && (
          <div>
            {/* Display Name */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 4, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Display Name
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={editingDisplayName}
                  onChange={e => setEditingDisplayName(e.target.value)}
                  placeholder="Your display name"
                  onKeyDown={e => { if (e.key === 'Enter') handleSaveDisplayName() }}
                  style={{
                    flex: 1, padding: '8px 10px', borderRadius: 6, fontSize: 12,
                    background: c.bg, color: c.heading,
                    border: `1px solid ${c.border}`, outline: 'none',
                    fontFamily: "var(--body-font, 'Lora'), serif",
                  }}
                />
                <button
                  onClick={handleSaveDisplayName}
                  disabled={saving}
                  style={{
                    padding: '8px 14px', borderRadius: 6,
                    background: saved ? '#059669' : c.accent, color: '#fff',
                    border: 'none', cursor: 'pointer', fontSize: 11,
                    fontWeight: 600, whiteSpace: 'nowrap',
                  }}
                >
                  {saved ? 'Saved!' : saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>

            {/* Default Act */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 4, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Default Act
              </label>
              <select
                value={userPrefs?.default_act || 'itaa-1997'}
                onChange={e => { setDefaultAct(e.target.value); savePrefs({ default_act: e.target.value } as any) }}
                style={{
                  width: '100%', padding: '8px 10px', borderRadius: 6, fontSize: 12,
                  background: c.bg, color: c.heading,
                  border: `1px solid ${c.border}`, outline: 'none',
                  fontFamily: "var(--heading-font, 'Montserrat'), sans-serif",
                  cursor: 'pointer',
                }}
              >
                {(acts.length > 0 ? acts : [{ id: 'itaa-1997', name: 'ITAA 1997' }, { id: 'itaa-1936', name: 'ITAA 1936' }]).map(a => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {tab === 'appearance' && (
          <div>
            {/* Theme toggle */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 6, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Theme
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                {['dark', 'light'].map(t => (
                  <button
                    key={t}
                    onClick={() => handleThemeToggle(t)}
                    style={{
                      flex: 1, padding: '8px 12px', borderRadius: 6,
                      background: theme === t ? c.accent : c.bg,
                      color: theme === t ? '#fff' : c.text,
                      border: `1px solid ${theme === t ? c.accent : c.border}`,
                      cursor: 'pointer', fontSize: 11,
                      fontWeight: theme === t ? 600 : 400,
                      fontFamily: "var(--heading-font, 'Montserrat'), sans-serif",
                      textTransform: 'capitalize',
                    }}
                  >{t}</button>
                ))}
              </div>
            </div>

            {/* Accent Color */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 6, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Accent Color
              </label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {ACCENT_PRESETS.map(color => (
                  <button
                    key={color}
                    onClick={() => handleAccent(color)}
                    title={color}
                    style={{
                      width: 28, height: 28, borderRadius: 6,
                      background: color, border: accentColor === color ? '2px solid #fff' : `1px solid ${c.border}`,
                      cursor: 'pointer', outline: accentColor === color ? `2px solid ${color}` : 'none',
                      outlineOffset: 1,
                    }}
                  />
                ))}
                <div style={{ position: 'relative' }}>
                  <input
                    type="color"
                    value={accentColor}
                    onChange={e => handleAccent(e.target.value)}
                    style={{
                      width: 28, height: 28, borderRadius: 6, padding: 0,
                      border: `1px solid ${c.border}`, cursor: 'pointer',
                      background: 'transparent',
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Heading Font */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 4, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Heading Font
              </label>
              <select
                value={headingFont}
                onChange={e => handleHeadingFont(e.target.value)}
                style={{
                  width: '100%', padding: '8px 10px', borderRadius: 6, fontSize: 12,
                  background: c.bg, color: c.heading,
                  border: `1px solid ${c.border}`, outline: 'none',
                  fontFamily: e => e ? e.target.value : "'Montserrat', sans-serif",
                  cursor: 'pointer',
                }}
              >
                {FONTS.heading.map(f => (
                  <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>
                ))}
              </select>
            </div>

            {/* Body Font */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 11, color: c.textMuted, display: 'block', marginBottom: 4, fontFamily: "var(--heading-font, 'Montserrat'), sans-serif" }}>
                Body Font
              </label>
              <select
                value={bodyFont}
                onChange={e => handleBodyFont(e.target.value)}
                style={{
                  width: '100%', padding: '8px 10px', borderRadius: 6, fontSize: 12,
                  background: c.bg, color: c.heading,
                  border: `1px solid ${c.border}`, outline: 'none',
                  fontFamily: "'Montserrat', sans-serif",
                  cursor: 'pointer',
                }}
              >
                {FONTS.body.map(f => (
                  <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>
                ))}
              </select>
              <div style={{ marginTop: 8, fontSize: 13, color: c.text, fontFamily: `'${bodyFont}', ${bodyFont === 'serif' ? 'serif' : 'sans-serif'}`, lineHeight: 1.6, padding: 12, background: c.bg, borderRadius: 6, border: `1px solid ${c.border}` }}>
                The quick brown fox jumps over the lazy dog. <span style={{ color: c.accent }}>Section 8-1</span> of the ITAA 1997.
              </div>
            </div>

            {/* Reset */}
            <button
              onClick={handleReset}
              style={{
                width: '100%', padding: '10px', borderRadius: 6,
                background: 'transparent', color: '#ef4444',
                border: `1px solid #ef4444`, cursor: 'pointer',
                fontSize: 12, fontWeight: 600,
                fontFamily: "var(--heading-font, 'Montserrat'), sans-serif",
              }}
            >
              Reset to Defaults
            </button>
          </div>
        )}
      </div>
    </div>
  )
}