import React, { useState, useEffect } from 'react';
import { LinkIcon, CheckCircle2, XCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const IntegrationIcon = ({ name, displayName }) => {
  if (name === 'github') {
    return (
      <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
      </svg>
    );
  }
  if (name === 'jira') {
    return (
      <svg viewBox="0 0 24 24" width="24" height="24" fill="#2684FF">
        <path d="M11.53 17.53c-2.48 2.48-6.52 2.48-9 0L.4 15.4l5.37-5.37c1.19-1.19 3.12-1.19 4.31 0l5.77 5.76-4.32 4.31v-2.57zM11.53 6.47c2.48-2.48 6.52-2.48 9 0l2.13 2.13-5.37 5.37c-1.19 1.19-3.12 1.19-4.31 0L7.21 8.21l4.32-4.31v2.57z"/>
        <path d="M23.6 15.4l-2.13 2.13c-2.48 2.48-6.52 2.48-9 0l-5.77-5.76 4.32-4.31c1.19-1.19 3.12-1.19 4.31 0l5.37 5.37c1.2 1.19 1.2 3.12 0 4.31M.4 8.6l2.13-2.13c2.48-2.48 6.52-2.48 9 0l5.77 5.76-4.32 4.31c-1.19 1.19-3.12 1.19-4.31 0L3.3 11.17C2.1 9.98 2.1 8.05.4 8.6"/>
      </svg>
    );
  }
  if (name === 'google_workspace' || name === 'google') {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    );
  }
  
  return <span>{displayName.charAt(0)}</span>;
};

const ProfileConnectors = () => {
  const { authFetch } = useAuth();
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [patToken, setPatToken] = useState('');
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      const res = await authFetch('/api/v1/integrations');
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data);
      } else {
        setError('Failed to load integrations');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openConnectModal = (integration) => {
    setSelectedIntegration(integration);
    setPatToken('');
    setIsModalOpen(true);
  };

  const handleConnect = async () => {
    if (!patToken.trim()) return;

    try {
      setConnecting(true);
      setError(null);
      const res = await authFetch(`/api/v1/integrations/${selectedIntegration.name}/pat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: patToken.trim() })
      });

      if (res.ok) {
        setSuccessMsg(`Successfully connected to ${selectedIntegration.display_name}`);
        setIsModalOpen(false);
        fetchIntegrations();
        setTimeout(() => setSuccessMsg(null), 3000);
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to connect');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async (integration) => {
    if (!window.confirm(`Are you sure you want to disconnect ${integration.display_name}?`)) return;

    try {
      const res = await authFetch(`/api/v1/integrations/${integration.name}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        setSuccessMsg(`Successfully disconnected from ${integration.display_name}`);
        fetchIntegrations();
        setTimeout(() => setSuccessMsg(null), 3000);
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to disconnect');
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const getModalText = (integrationName) => {
    switch (integrationName) {
      case 'github':
        return {
          description: "Please enter your GitHub Personal Access Token (PAT). Ensure it has the 'repo' and 'read:org' scopes.",
          label: "Personal Access Token",
          placeholder: "ghp_xxxxxxxxxxxxxxxxxxxx"
        };
      case 'jira':
        return {
          description: "Please enter your Jira API Token. You can generate this from your Atlassian account security settings.",
          label: "Jira API Token",
          placeholder: "ATATT3x..."
        };
      case 'google_workspace':
      case 'google':
        return {
          description: "Please enter your Google Workspace OAuth Token or Service Account JSON (Base64 encoded).",
          label: "Google Access Token",
          placeholder: "ya29.a0..."
        };
      default:
        return {
          description: "Please enter your access token or API key for this service.",
          label: "Access Token",
          placeholder: "Token..."
        };
    }
  };

  const modalText = selectedIntegration ? getModalText(selectedIntegration.name) : getModalText('');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', width: '100%', maxWidth: '800px' }} className="animate-fade-in">
      <div>
        <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <LinkIcon style={{ color: 'var(--accent-primary)', width: '32px', height: '32px' }} /> Connectors
        </h1>
        <p style={{ marginTop: '0.5rem', fontSize: '1.125rem', color: 'var(--text-secondary)' }}>
          Manage your third-party integrations.
        </p>
      </div>

      {error && (
        <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '1rem', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <XCircle size={20} color="#f87171" />
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#86efac', padding: '1rem', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <CheckCircle2 size={20} color="#4ade80" />
          {successMsg}
        </div>
      )}

      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading integrations...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {integrations.map((integration, index) => (
              <div key={integration.name} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1.5rem',
                borderBottom: index < integrations.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                transition: 'background-color 0.2s'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    backgroundColor: 'rgba(255,255,255,0.05)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    border: '1px solid rgba(255,255,255,0.1)'
                  }}>
                    <IntegrationIcon name={integration.name} displayName={integration.display_name} />
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>{integration.display_name}</h3>
                    <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{integration.description || `Connect to ${integration.display_name}`}</p>
                  </div>
                </div>

                <div>
                  {integration.is_connected ? (
                    <button
                      onClick={() => handleDisconnect(integration)}
                      className="btn"
                      style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.2)', minWidth: '120px' }}
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={() => openConnectModal(integration)}
                      className="btn btn-primary"
                      style={{ minWidth: '120px' }}
                    >
                      Connect
                    </button>
                  )}
                </div>
              </div>
            ))}

            {integrations.length === 0 && (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                No integrations configured in the database.
              </div>
            )}
          </div>
        )}
      </div>

      {/* PAT Modal */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(4px)',
          padding: '1rem'
        }}>
          <div className="glass-panel animate-slide-up" style={{ width: '100%', maxWidth: '450px', padding: '2rem' }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Connect {selectedIntegration?.display_name}
            </h3>
            <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {modalText.description}
            </p>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                {modalText.label}
              </label>
              <input
                type="password"
                value={patToken}
                onChange={(e) => setPatToken(e.target.value)}
                className="input-field"
                placeholder={modalText.placeholder}
                autoFocus
                style={{ width: '100%', padding: '0.75rem 1rem' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn"
                disabled={connecting}
              >
                Cancel
              </button>
              <button
                onClick={handleConnect}
                disabled={!patToken.trim() || connecting}
                className="btn btn-primary"
              >
                {connecting ? 'Connecting...' : 'Connect Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileConnectors;
