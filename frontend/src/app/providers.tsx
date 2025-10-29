import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Theme Provider (light/dark via class on <html>)
type Theme = 'light' | 'dark' | 'system'
const ThemeContext = createContext<{ theme: Theme; setTheme: (t: Theme) => void }>({ theme: 'system', setTheme: () => {} })

function applyTheme(t: Theme) {
  const root = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = t === 'dark' || (t === 'system' && prefersDark)
  root.classList.toggle('dark', isDark)
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => (localStorage.getItem('theme') as Theme) || 'system')
  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem('theme', t)
    setThemeState(t)
    applyTheme(t)
  }, [])

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    const listener = (e: MediaQueryListEvent) => {
      if ((localStorage.getItem('theme') as Theme) === 'system') applyTheme('system')
    }
    const mql = window.matchMedia('(prefers-color-scheme: dark)')
    mql.addEventListener('change', listener)
    return () => mql.removeEventListener('change', listener)
  }, [])

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  return useContext(ThemeContext)
}

// Minimal Toast system
type Toast = { id: number; title?: string; description?: string }
const ToastContext = createContext<{ notify: (t: Omit<Toast, 'id'>) => void }>({ notify: () => {} })

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const idRef = useRef(1)
  const notify = useCallback((t: Omit<Toast, 'id'>) => {
    const id = idRef.current++
    setToasts((prev) => [...prev, { id, ...t }])
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 3000)
  }, [])

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="fixed z-50 top-3 right-3 space-y-2">
        {toasts.map((t) => (
          <div key={t.id} className="min-w-[240px] max-w-sm rounded-md border border-gray-200/60 dark:border-gray-800 bg-white/90 dark:bg-black/70 shadow-md p-3">
            {t.title && <div className="text-sm font-medium mb-0.5">{t.title}</div>}
            {t.description && <div className="text-xs text-gray-600 dark:text-gray-300">{t.description}</div>}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}

// App Providers wrapper
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 60_000,
      retry: 1,
    },
  },
})

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>{children}</ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}


