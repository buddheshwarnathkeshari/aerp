import React, { useState, useEffect } from 'react';
import { LinkIcon, CheckCircle2, XCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import IntegrationIcon from '../components/IntegrationIcon';

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
