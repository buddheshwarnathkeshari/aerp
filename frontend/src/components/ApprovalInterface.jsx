import React, { useState } from 'react'
import axios from 'axios'
import { Check, X, AlertCircle } from 'lucide-react'
import FindingsViewer from './FindingsViewer'

const API_BASE = ''

export default function ApprovalInterface({ reviewId, prUrl, review, findings, onApproved }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleApprove = async () => {
    setLoading(true)
    try {
      await axios.post(`${API_BASE}/reviews/${reviewId}/approve`, {
        comment: 'Approved by Human via AERP UI'
      })
      onApproved()
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to approve review.')
      setLoading(false)
    }
  }

  return (
    <div className="flex-col gap-6" style={{ marginTop: '2rem' }}>
      {/* Warning Banner */}
      <div className="glass-panel animate-slide-up" style={{ borderColor: 'var(--accent-warning)', boxShadow: '0 0 20px rgba(245,158,11,0.15)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '2rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, color: 'var(--accent-warning)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem' }}>
              <AlertCircle size={24} /> Human-In-The-Loop Required
            </h2>
            <p style={{ margin: '0.5rem 0 0 0' }}>
              The AI calculated a risk score of{' '}
              <strong style={{ color: review.risk_score > 60 ? 'var(--accent-danger)' : 'var(--accent-warning)' }}>
                {review.risk_score ?? 'N/A'}
              </strong>
              , which exceeds the threshold. Please review findings below before approving.
            </p>
            {prUrl && (
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
                PR:{' '}
                <a href={prUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}>
                  {prUrl.replace('https://github.com/', '')}
                </a>
              </p>
            )}
            {error && <p style={{ color: 'var(--accent-danger)', marginTop: '0.75rem', fontSize: '0.875rem' }}>{error}</p>}
          </div>
          
          <div className="flex gap-4" style={{ flexShrink: 0 }}>
            <button
              className="btn btn-secondary"
              style={{ color: 'var(--accent-danger)', borderColor: 'rgba(239,68,68,0.4)' }}
              onClick={() => alert('Reject flow is not implemented in this phase.')}
              disabled={loading}
            >
              <X size={16} /> Reject
            </button>
            <button
              className="btn btn-success"
              onClick={handleApprove}
              disabled={loading}
              style={{ padding: '0.625rem 1.5rem' }}
            >
              {loading ? 'Approving...' : <><Check size={16} /> Approve & Generate PRs</>}
            </button>
          </div>
        </div>
      </div>

      {/* Findings */}
      <h3>Critical AI Findings — Review Before Approving</h3>
      <FindingsViewer findings={findings || []} reviewId={reviewId} />
    </div>
  )
}
