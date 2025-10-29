import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../lib/api'

type Sentiment = { positive: number; neutral: number; negative: number }
type Keyword = { keyword: string; count: number }

export default function Dashboard() {
  const { companyId = '' } = useParams()

  const sentiment = useQuery({
    queryKey: ['sentiment', companyId],
    queryFn: () => apiGet<Sentiment>(`/api/sentiment/${companyId}`),
    enabled: !!companyId,
    refetchInterval: 30_000
  })

  const keywords = useQuery({
    queryKey: ['keywords', companyId],
    queryFn: () => apiGet<Keyword[]>(`/api/keywords/${companyId}`),
    enabled: !!companyId
  })

  return (
    <div className="min-h-screen mx-auto max-w-6xl p-6">
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-sm text-gray-500">← Companies</Link>
          <h1 className="text-2xl font-semibold">{companyId.replace(/[_-]/g,' ').toUpperCase()}</h1>
        </div>
      </header>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="rounded-xl border p-4">
          <div className="text-sm text-gray-500 mb-2">Live Sentiment</div>
          {sentiment.isLoading ? (
            <div className="h-24 bg-gray-200 dark:bg-gray-800 animate-pulse rounded-md" />
          ) : (
            <div className="flex gap-6">
              <Stat label="Positive" value={sentiment.data?.positive ?? 0} color="text-emerald-600" />
              <Stat label="Neutral" value={sentiment.data?.neutral ?? 0} color="text-slate-600" />
              <Stat label="Negative" value={sentiment.data?.negative ?? 0} color="text-rose-600" />
            </div>
          )}
        </div>

        <div className="rounded-xl border p-4 md:col-span-2">
          <div className="text-sm text-gray-500 mb-2">Top Keywords</div>
          {keywords.isLoading ? (
            <div className="h-36 bg-gray-200 dark:bg-gray-800 animate-pulse rounded-md" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {(keywords.data ?? []).map(k => (
                <span key={k.keyword} className="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-sm">
                  {k.keyword} <span className="text-gray-500">{k.count}</span>
                </span>
              ))}
              {(keywords.data ?? []).length === 0 && <div className="text-sm text-gray-500">No keywords.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div>
      <div className={`text-2xl font-semibold ${color ?? ''}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )
}


