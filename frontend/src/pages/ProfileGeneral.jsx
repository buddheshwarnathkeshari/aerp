import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Save } from 'lucide-react';

const ProfileGeneral = () => {
  const { user, authFetch, fetchCurrentUser } = useAuth();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [profileMessage, setProfileMessage] = useState({ text: '', type: '' });
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
    }
  }, [user]);

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileMessage({ text: '', type: '' });
    
    try {
      const response = await authFetch('/api/v1/auth/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: firstName.trim() || null,
          last_name: lastName.trim() || null
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to update profile');
      }
      
      await fetchCurrentUser();
      setProfileMessage({ text: 'Profile updated successfully!', type: 'success' });
    } catch (err) {
      setProfileMessage({ text: err.message, type: 'error' });
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      <div>
        <h1 style={{ fontSize: '1.875rem', fontWeight: 700, margin: 0, letterSpacing: '-0.025em' }}>General Info</h1>
        <p className="text-sm m-0 mt-1" style={{ color: 'var(--text-secondary)' }}>Manage your personal information.</p>
      </div>

      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
          <div style={{ padding: '0.5rem', background: 'rgba(59, 130, 246, 0.1)', color: 'rgb(59, 130, 246)', borderRadius: '8px' }}>
            <User size={20} />
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>Profile Details</h2>
        </div>
        
        {profileMessage.text && (
          <div style={{ padding: '0.75rem', borderRadius: '8px', background: profileMessage.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)', border: '1px solid ' + (profileMessage.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'), color: profileMessage.type === 'error' ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)', fontSize: '0.875rem' }}>
            {profileMessage.text}
          </div>
        )}

        <form onSubmit={handleProfileUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: 500 }}>Email Address</label>
            <input type="email" value={user?.email || ''} disabled className="input-field" style={{ opacity: 0.6, cursor: 'not-allowed', width: '100%' }} />
          </div>
          
          <div style={{ display: 'flex', gap: '1rem', width: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', flex: 1 }}>
              <label htmlFor="editFirstName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>First Name</label>
              <input id="editFirstName" type="text" className="input-field" style={{ width: '100%' }} value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', flex: 1 }}>
              <label htmlFor="editLastName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Last Name</label>
              <input id="editLastName" type="text" className="input-field" style={{ width: '100%' }} value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>

          <button type="submit" disabled={profileLoading} className="btn btn-primary" style={{ marginTop: '0.5rem', alignSelf: 'flex-start' }}>
            <Save size={16} /> Save Changes
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProfileGeneral;
