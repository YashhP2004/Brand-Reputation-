import { createBrowserRouter } from 'react-router-dom'
import Home from '../pages/Home'
import Dashboard from '../pages/Dashboard'
import NotFound from '../pages/NotFound'

export const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/dashboard/:companyId', element: <Dashboard /> },
  { path: '*', element: <NotFound /> }
])


