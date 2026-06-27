import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { Clock, CheckCircle, AlertTriangle, ShieldAlert, GitPullRequest } from 'lucide-react'

const API_BASE = ''

export default function ReviewHistory() {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await axios.get(`${API_BASE}/reviews`)
        setReviews(res.data.reviews || [])
      } catch (err) {
        console.error("Failed to load review history", err)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [])

  if (loading) {
    return <div className="text-center" style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading history...</div>
  }

  if (reviews.length === 0) {
    return null // Don't show anything if no history
  }

  return (
    <div className="glass-panel" style={{ marginTop: '3rem', width: '100%', maxWidth: '800px', margin: '3rem auto 0 auto' }}>
      <h3 style={{ margin: '0 0 1.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Clock size={20} /> Recent Reviews
      </h3>
      
      <div className="flex-col gap-3">
        {reviews.map(review => (
          <Link 
            key={review.id} 
            to={`/review/${review.id}?pr_url=${encodeURIComponent(review.pr_url)}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div 
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                transition: 'all 0.2s ease',
                cursor: 'pointer',
              }}
              className="hover-brighten"
            >
              <div className="flex items-center gap-4">
                <StatusIcon status={review.status} />
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <GitPullRequest size={14} /> 
                    {review.pr_url.replace('https://github.com/', '')}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {new Date(review.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-6">
                <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                  {review.status.replace(/_/g, ' ')}
                </div>
                {review.risk_score != null ? (
                  <div style={{ 
                    fontSize: '1rem', 
                    fontWeight: 700, 
                    color: review.risk_score > 60 ? 'var(--accent-danger)' : review.risk_score > 30 ? 'var(--accent-warning)' : 'var(--accent-success)',
                    width: '40px',
                    textAlign: 'right'
                  }}>
                    {review.risk_score}
                  </div>
                ) : (
                  <div style={{ width: '40px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.8rem' }}>--</div>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

function StatusIcon({ status }) {
  if (status === 'complete') return <CheckCircle size={18} color="var(--accent-success)" />
  if (status === 'failed') return <AlertTriangle size={18} color="var(--accent-danger)" />
  if (status === 'paused_for_review' || status === 'awaiting_human') return <ShieldAlert size={18} color="var(--accent-warning)" />
  return <Clock size={18} color="var(--accent-primary)" className="animate-spin-slow" />
}
