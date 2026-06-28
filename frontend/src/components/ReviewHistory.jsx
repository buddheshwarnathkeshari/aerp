import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { Clock, CheckCircle, AlertTriangle, ShieldAlert, GitPullRequest, Inbox } from 'lucide-react'

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



  return (
    <div className="animate-fade-in" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', padding: 0 }}>
      <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(255,255,255,0.01)' }}>
        <Clock size={20} style={{ color: 'var(--accent-primary)' }} /> 
        <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>Recent Reviews</h3>
      </div>
      
      <div className="flex-col gap-3" style={{ padding: '1.5rem 2rem', flex: 1, overflowY: 'auto' }}>
        {reviews.length === 0 ? (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '400px', color: 'var(--text-muted)' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(255,255,255,0.03)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem' }}>
              <Inbox size={32} style={{ opacity: 0.4 }} />
            </div>
            <p style={{ fontSize: '1.1rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No reviews yet</p>
            <p style={{ fontSize: '0.9rem', textAlign: 'center', maxWidth: '250px', lineHeight: 1.5 }}>
              Submit a GitHub or Jira URL on the left to kick off your first Multi-Agent AI review.
            </p>
          </div>
        ) : (
          reviews.map(review => (
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
                padding: '1.25rem',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.05)',
                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div className="flex items-center gap-4">
                <StatusIcon status={review.status} />
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <GitPullRequest size={14} style={{ flexShrink: 0 }} /> 
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '280px' }}>
                      {review.pr_url.replace('https://github.com/', '')}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {new Date(review.created_at).toLocaleString()}
                    {review.llm_provider && (
                      <span style={{ marginLeft: '0.5rem', padding: '0.1rem 0.4rem', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', fontSize: '0.65rem', textTransform: 'capitalize' }}>
                        {review.llm_provider === 'ollama' ? review.llm_model : review.llm_provider}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-6" style={{ flexShrink: 0 }}>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', width: '120px', textAlign: 'right' }}>
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
          ))
        )}
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
