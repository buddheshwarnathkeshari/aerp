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
    <div className="flex-col justify-start items-center" style={{ flex: 1, marginTop: '5vh' }}>
      <div className="glass-panel animate-slide-up" style={{ width: '100%', maxWidth: '500px' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>Start Code Review</h2>
        <p style={{ textAlign: 'center', marginBottom: '2rem', fontSize: '0.875rem' }}>
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

      <ReviewHistory />
    </div>
  )
}
