import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="text-center">
        <div className="text-6xl font-bold mb-2">404</div>
        <p className="text-gray-500 mb-6">Page not found.</p>
        <Link className="px-3 py-1.5 rounded-md bg-brand text-white" to="/">Go Home</Link>
      </div>
    </div>
  )
}


