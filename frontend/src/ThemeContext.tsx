import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

export interface ThemeConfig {
  bg: string
  surface: string
  surfaceHover: string
  border: string
  text: string
  textMuted: string
  accent: string
  accentHover: string
  heading: string
}

const DARK: ThemeConfig = {
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

const LIGHT: ThemeConfig = {
  bg: '#f8fafc',
  surface: '#ffffff',
  surfaceHover: '#f1f5f9',
  border: '#e2e8f0',
  text: '#334155',
  textMuted: '#64748b',
  accent: '#279e88',
  accentHover: '#1f5858',
  heading: '#0f172a',
}

const FONTS = {
  heading: ['Montserrat', 'Inter', 'Roboto', 'system-ui'],
  body: ['Lora', 'Merriweather', 'Georgia', 'serif', 'system-ui'],
}

export interface UserPrefs {
  display_name: string
  default_act: string
  theme: string
  accent_color: string
  heading_font: string
  body_font: string
}

interface ThemeContextValue {
  colors: ThemeConfig
  theme: string
  accentColor: string
  headingFont: string
  bodyFont: string
  userPrefs: UserPrefs | null
  setTheme: (t: string) => void
  setAccentColor: (c: string) => void
  setHeadingFont: (f: string) => void
  setBodyFont: (f: string) => void
  setDisplayName: (n: string) => void
  setDefaultAct: (a: string) => void
  resetTheme: () => void
  refreshPrefs: () => Promise<void>
  savePrefs: (updates: Partial<UserPrefs>) => Promise<void>
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function baseColors(theme: string, accent: string): ThemeConfig {
  const base = theme === 'light' ? { ...LIGHT } : { ...DARK }
  base.accent = accent
  base.accentHover = theme === 'light' ? '#1a6f5e' : '#1f5858'
  return base
}

const DEFAULT_PREFS: UserPrefs = {
  display_name: '',
  default_act: 'itaa-1997',
  theme: 'dark',
  accent_color: '#279e88',
  heading_font: 'Montserrat',
  body_font: 'Lora',
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [userPrefs, setUserPrefs] = useState<UserPrefs | null>(() => {
    try {
      const cached = localStorage.getItem('legislation-user-prefs')
      return cached ? JSON.parse(cached) : null
    } catch { return null }
  })

  const colors = baseColors(
    userPrefs?.theme || 'dark',
    userPrefs?.accent_color || '#279e88',
  )

  const setTheme = useCallback((t: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), theme: t }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const setAccentColor = useCallback((c: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), accent_color: c }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const setHeadingFont = useCallback((f: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), heading_font: f }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const setBodyFont = useCallback((f: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), body_font: f }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const setDisplayName = useCallback((n: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), display_name: n }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const setDefaultAct = useCallback((a: string) => {
    setUserPrefs(prev => {
      const next = { ...(prev || DEFAULT_PREFS), default_act: a }
      localStorage.setItem('legislation-user-prefs', JSON.stringify(next))
      return next
    })
  }, [])

  const resetTheme = useCallback(() => {
    const defaults = { ...DEFAULT_PREFS }
    setUserPrefs(defaults)
    localStorage.setItem('legislation-user-prefs', JSON.stringify(defaults))
  }, [])

  const refreshPrefs = useCallback(async () => {
    try {
      const r = await fetch('/api/user/prefs')
      if (r.ok) {
        const data = await r.json()
        setUserPrefs(data)
        localStorage.setItem('legislation-user-prefs', JSON.stringify(data))
      }
    } catch {}
  }, [])

  const savePrefs = useCallback(async (updates: Partial<UserPrefs>) => {
    try {
      const r = await fetch('/api/user/prefs', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (r.ok) {
        const data = await r.json()
        setUserPrefs(data)
        localStorage.setItem('legislation-user-prefs', JSON.stringify(data))
      }
    } catch {}
  }, [])

  // Sync from backend on mount (if logged in)
  useEffect(() => {
    refreshPrefs()
  }, [refreshPrefs])

  const value: ThemeContextValue = {
    colors,
    theme: userPrefs?.theme || 'dark',
    accentColor: userPrefs?.accent_color || '#279e88',
    headingFont: userPrefs?.heading_font || 'Montserrat',
    bodyFont: userPrefs?.body_font || 'Lora',
    userPrefs,
    setTheme,
    setAccentColor,
    setHeadingFont,
    setBodyFont,
    setDisplayName,
    setDefaultAct,
    resetTheme,
    refreshPrefs,
    savePrefs,
  }

  return (
    <ThemeContext.Provider value={value}>
      <div style={{
        '--heading-font': value.headingFont,
        '--body-font': value.bodyFont,
      } as React.CSSProperties}>
        {children}
      </div>
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

export { DARK, LIGHT, FONTS }