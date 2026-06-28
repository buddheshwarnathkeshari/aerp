import React, { useState, useEffect, useRef } from 'react'
import { ShieldAlert, Bug, FileCode, CheckCircle, Info, Send, ChevronDown, Edit2, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { createPortal } from 'react-dom'
import axios from 'axios'

export default function FindingsViewer({ findings, reviewId }) {
  if (!findings || findings.length === 0) {
    return (
      <div className="glass-panel text-center" style={{ padding: '3rem' }}>
        <CheckCircle size={48} color="var(--accent-success)" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ margin: 0 }}>No Issues Found</h3>
        <p style={{ margin: '0.5rem 0 0 0' }}>The agents did not find any significant issues with this PR.</p>
      </div>
    )
  }

  // Group by agent
  const grouped = findings.reduce((acc, finding) => {
    const agent = finding.agent || finding.agent_name || 'General'
    if (!acc[agent]) acc[agent] = []
    acc[agent].push(finding)
    return acc
  }, {})

  return (
    <div className="flex-col gap-6">
      {Object.entries(grouped).map(([agentName, agentFindings]) => (
        <div key={agentName} className="glass-panel">
          <h3 style={{ 
            textTransform: 'capitalize', 
            borderBottom: '1px solid var(--border-color)', 
            paddingBottom: '0.75rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            {getAgentIcon(agentName)}
            {agentName.replace('_agent', ' Agent')}
          </h3>
          
          <div className="flex-col gap-4">
            {agentFindings.map((f, i) => (
              <FindingCard key={i} finding={f} reviewId={reviewId} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function FindingCard({ finding, reviewId }) {
  const [isPosting, setIsPosting] = useState(false)
  const [posted, setPosted] = useState(finding.included_in_pr || false)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [dropdownRef])

  const generateDefaultMessage = () => {
    let msg = `## AERP AI Review Finding\n\n### [${(finding.severity || 'medium').toUpperCase()}] ${finding.title || 'Issue'}\n**File:** \`${finding.file_path || 'General'}\`\n\n${finding.description}\n\n`;
    if (finding.evidence) {
      msg += `**Evidence:**\n\`\`\`\n${finding.evidence}\n\`\`\`\n\n`;
    }
    return msg;
  }

  const handlePostToPR = async (editedMessage = null) => {
    if (!reviewId || !finding.id) return;
    setIsPosting(true)
    try {
      const payload = {}
      if (editedMessage) {
        payload.edited_message = editedMessage
      }
      const res = await axios.post(`/reviews/${reviewId}/findings/${finding.id}/post`, payload)
      if (res.status === 200 || res.status === 201) {
        setPosted(true)
      }
    } catch (err) {
      console.error("Failed to post finding to PR", err)
    } finally {
      setIsPosting(false)
    }
  }

  const severityColors = {
    critical: 'var(--accent-danger)',
    high: 'var(--accent-danger)',
    medium: 'var(--accent-warning)',
    low: 'var(--accent-primary)',
    info: 'var(--text-secondary)'
  }

  const severity = (finding.severity || 'info').toLowerCase()
  const color = severityColors[severity] || severityColors.info

  return (
    <div style={{ 
      background: 'rgba(15, 23, 42, 0.4)', 
      borderLeft: `4px solid ${color}`,
      borderRadius: '0 8px 8px 0',
      padding: '1rem',
      position: 'relative'
    }}>
      <div className="flex justify-between items-center mb-2">
        <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>{finding.title || 'Finding'}</h4>
        <span className="badge" style={{ backgroundColor: `${color}33`, color: color }}>
          {severity.toUpperCase()}
        </span>
      </div>
      
      <div className="mb-3 markdown-content">
        <ReactMarkdown>
          {finding.description}
        </ReactMarkdown>
      </div>
      
      <div className="flex justify-between items-end" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <div>
          {finding.file_path && <span><FileCode size={12} className="inline mr-1" /> {finding.file_path}</span>}
          {finding.line_number && <span style={{ marginLeft: '0.5rem' }}>Line {finding.line_number}</span>}
        </div>
        <div className="flex items-center gap-4">
          <span>Confidence: {finding.confidence != null ? (finding.confidence * 100).toFixed(0) : 0}%</span>
          {reviewId && finding.id && (
            <div style={{ position: 'relative' }} ref={dropdownRef}>
              {posted ? (
                <button className="btn btn-small btn-success" disabled style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}>
                  <CheckCircle size={12} /> Posted
                </button>
              ) : (
                <>
                  <button 
                    className="btn btn-small btn-outline"
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    disabled={isPosting}
                    style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                  >
                    {isPosting ? 'Posting...' : <><Send size={12} /> Post to PR <ChevronDown size={12} /></>}
                  </button>
                  
                  {isDropdownOpen && !isPosting && (
                    <div style={{ 
                      position: 'absolute', 
                      right: 0, 
                      top: 'calc(100% + 0.25rem)', 
                      background: '#1e293b', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: '6px', 
                      zIndex: 10,
                      minWidth: '150px',
                      boxShadow: '0 10px 25px rgba(0,0,0,0.8)',
                      overflow: 'hidden'
                    }}>
                      <button 
                        onClick={() => { handlePostToPR(); setIsDropdownOpen(false); }}
                        style={{ display: 'block', width: '100%', padding: '0.5rem 1rem', textAlign: 'left', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.8rem' }}
                        className="hover-brighten"
                      >
                        Post directly
                      </button>
                      <button 
                        onClick={() => { setIsModalOpen(true); setIsDropdownOpen(false); }}
                        style={{ display: 'block', width: '100%', padding: '0.5rem 1rem', textAlign: 'left', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.8rem', borderTop: '1px solid var(--border-color)' }}
                        className="hover-brighten"
                      >
                        <Edit2 size={12} className="inline mr-1" /> Edit & Post
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {isModalOpen && createPortal(
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999 
        }}>
          <div className="glass-panel animate-slide-up" style={{ width: '90%', maxWidth: '600px', padding: '1.5rem' }}>
            <div className="flex justify-between items-center mb-4">
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Edit2 size={18} /> Edit PR Comment
              </h3>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>
            
            <textarea 
              className="input-field"
              style={{ width: '100%', height: '250px', fontFamily: 'monospace', fontSize: '0.85rem', padding: '1rem', resize: 'vertical' }}
              defaultValue={generateDefaultMessage()}
              id={`edit-comment-${finding.id}`}
            />
            
            <div className="flex justify-end gap-3 mt-4">
              <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => {
                const val = document.getElementById(`edit-comment-${finding.id}`).value;
                handlePostToPR(val);
                setIsModalOpen(false);
              }}>
                <Send size={16} /> Post Edited Comment
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}

function getAgentIcon(agentName) {
  if (agentName.includes('security')) return <ShieldAlert size={20} color="var(--accent-danger)" />
  if (agentName.includes('bug') || agentName.includes('code')) return <Bug size={20} color="var(--accent-warning)" />
  if (agentName.includes('architecture')) return <FileCode size={20} color="var(--accent-primary)" />
  return <Info size={20} color="var(--text-secondary)" />
}
