import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Activity } from 'lucide-react'
import SubmitReview from './components/SubmitReview'
import ReviewDashboard from './components/ReviewDashboard'

function App() {
  return (
    <BrowserRouter>
      <header className="glass-panel" style={{ borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderRight: 'none', padding: '1rem 2rem' }}>
        <div className="container flex items-center justify-between" style={{ padding: 0 }}>
          <Link to="/" className="flex items-center gap-2" style={{ textDecoration: 'none', color: 'var(--text-primary)' }}>
            <div style={{ padding: '0.5rem', background: 'var(--accent-primary)', borderRadius: '8px', display: 'flex' }}>
              <Activity size={24} color="white" />
            </div>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>AERP</h1>
          </Link>
          <nav>
            <Link to="/" className="btn btn-primary">+ New Review</Link>
          </nav>
        </div>
      </header>

      <main className="container flex-col" style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<SubmitReview />} />
          <Route path="/review/:id" element={<ReviewDashboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
