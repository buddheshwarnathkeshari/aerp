import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Github, Trello, Rocket } from 'lucide-react'
import ReviewHistory from './ReviewHistory'

const API_BASE = ''

export default function SubmitReview() {
  const [prUrl, setPrUrl] = useState('')
  const [jiraUrl, setJiraUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prUrl) {
      setError('GitHub PR URL is required.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await axios.post(`${API_BASE}/reviews/start`, {
        pr_url: prUrl,
        jira_url: jiraUrl || undefined
      })
      navigate(`/review/${response.data.review_id}?pr_url=${encodeURIComponent(prUrl)}`)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to start review.')
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: 'calc(100vh - 73px)', overflow: 'hidden' }}>
      
      {/* LEFT SIDE: Review Form Container (Scrollable) */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem', overflowY: 'auto' }}>
        
        {/* Actual Form Content */}
        <div style={{ width: '100%', maxWidth: '560px', position: 'relative' }}>
          {/* Dual Glow Orb */}
          <div style={{ 
            position: 'absolute', top: '-15%', left: '-15%', right: '-15%', bottom: '-15%',
            background: 'radial-gradient(circle at top left, rgba(59,130,246,0.3) 0%, transparent 50%), radial-gradient(circle at bottom right, rgba(139,92,246,0.25) 0%, transparent 50%)',
            filter: 'blur(60px)', zIndex: -1 
          }} />
          
          <div className="glass-panel animate-slide-up" style={{ padding: '3rem 2.5rem' }}>
            <h2 style={{ marginBottom: '0.5rem', fontSize: '2.25rem', fontWeight: 700, letterSpacing: '-0.03em', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Start Code Review</h2>
            <p style={{ marginBottom: '2.5rem', fontSize: '0.9375rem', color: 'var(--text-secondary)' }}>
              Our Multi-Agent AI system will analyze your PR for architecture, security, and bugs.
            </p>

        {error && (
          <div style={{ padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-danger)', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.875rem', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex-col">
          <div className="input-group">
            <label className="input-label flex items-center gap-2">
              <Github size={16} /> GitHub Pull Request URL *
            </label>
            <input 
              type="url" 
              className="input-field" 
              placeholder="https://github.com/org/repo/pull/123"
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
              required
            />
          </div>

          <div className="input-group">
            <label className="input-label flex items-center gap-2">
              <Trello size={16} /> Jira Ticket URL (Optional)
            </label>
            <input 
              type="url" 
              className="input-field" 
              placeholder="https://jira.company.com/browse/PROJ-123"
              value={jiraUrl}
              onChange={(e) => setJiraUrl(e.target.value)}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary mt-4" 
            style={{ width: '100%', padding: '0.875rem' }}
            disabled={loading}
          >
            {loading ? (
              <span className="animate-pulse">Starting Agents...</span>
            ) : (
              <>
                <Rocket size={18} /> Launch Analysis
              </>
            )}
          </button>
        </form>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE: Recent Reviews Sidebar */}
      <div style={{ 
        display: 'flex',
        flexDirection: 'column',
        width: '650px',
        minWidth: '650px',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        background: 'rgba(17, 25, 40, 0.4)',
        boxShadow: '-10px 0 30px rgba(0,0,0,0.2)',
        position: 'relative'
      }}>
        <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
          <ReviewHistory />
        </div>
      </div>

    </div>
  )
}
