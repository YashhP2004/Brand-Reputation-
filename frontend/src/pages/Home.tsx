import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../lib/api'
import { Link } from 'react-router-dom'

type Company = { id: string; display_name: string }

export default function Home() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiGet<Company[]>('/api/companies'),
    staleTime: 60_000
  })

  return (
    <div className="min-h-screen mx-auto max-w-5xl p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Brand Reputation Analyzer</h1>
        <button onClick={() => refetch()} className="px-3 py-1.5 rounded-md bg-brand text-white text-sm">Refresh</button>
      </header>

      {isLoading && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-gray-200 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="p-4 rounded-md border border-rose-300 bg-rose-50 dark:bg-rose-900/20">
          Failed to load companies. Check API server.
        </div>
      )}

      {data && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((c) => (
            <Link key={c.id} to={`/dashboard/${encodeURIComponent(c.id)}`} className="block rounded-xl border p-4 hover:shadow-card transition shadow-sm bg-white/70 dark:bg-black/30 dark:border-gray-800">
              <div className="text-lg font-medium">{c.display_name}</div>
              <div className="text-xs text-gray-500">Open dashboard →</div>
            </Link>
          ))}
          {data.length === 0 && (
            <div className="col-span-full p-8 text-center border rounded-xl">No companies yet. Run an analysis to get started.</div>
          )}
        </div>
      )}
    </div>
  )
}


