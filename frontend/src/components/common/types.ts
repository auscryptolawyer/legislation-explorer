// Shared types and theme for the Legislation Explorer frontend

export const COLORS = {
  bg: '#0a1214',
  surface: '#0b1b1f',
  surfaceHover: '#141e20',
  border: '#253d3d',
  text: '#aebec2',
  textMuted: '#758696',
  accent: '#279e88',
  accentHover: '#1f5858',
  heading: '#ffffff',
} as const

export type Section = { id: string; title: string; path: string }
export type Subdivision = { id: string; title: string; sections: Section[] }
export type Division = { id: string; title: string; subdivisions: Subdivision[]; sections: Section[] }
export type Part = { id: string; title: string; divisions: Division[]; sections: Section[] }
export type Signpost = { id: string; title: string; is_signpost: true }
export type Tree = { act: string; parts: (Part | Division | Signpost)[] }

export type PinItem = { act: string; section: string; title: string }
export type HistoryItem = { act: string; section: string; title: string; timestamp: number }
