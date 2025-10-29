import { create } from 'zustand'

type WidgetKey =
  | 'sentiment'
  | 'keywords'
  | 'themes'
  | 'news'
  | 'reddit'
  | 'twitter'

type DashboardState = {
  companyId: string | null
  setCompanyId: (id: string | null) => void

  widgetOrder: WidgetKey[]
  setWidgetOrder: (order: WidgetKey[]) => void

  refreshIntervalMs: number
  setRefreshIntervalMs: (ms: number) => void

  liveUpdates: boolean
  setLiveUpdates: (v: boolean) => void
}

const defaultOrder: WidgetKey[] = [
  'sentiment',
  'keywords',
  'themes',
  'news',
  'reddit',
  'twitter',
]

export const useDashboardStore = create<DashboardState>((set) => ({
  companyId: null,
  setCompanyId: (id) => set({ companyId: id }),

  widgetOrder: defaultOrder,
  setWidgetOrder: (order) => set({ widgetOrder: order }),

  refreshIntervalMs: 30_000,
  setRefreshIntervalMs: (ms) => set({ refreshIntervalMs: ms }),

  liveUpdates: true,
  setLiveUpdates: (v) => set({ liveUpdates: v }),
}))


