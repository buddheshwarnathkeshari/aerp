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
          first_name: firstName,
          last_name: lastName
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
    <div className="flex flex-col gap-6 w-full max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold m-0 tracking-tight">General Info</h1>
        <p className="text-sm m-0 mt-1" style={{ color: 'var(--text-secondary)' }}>Manage your personal information.</p>
      </div>

      <div className="glass-panel p-6 flex flex-col gap-6">
        <div className="flex items-center gap-3 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
          <div style={{ padding: '0.5rem', background: 'rgba(59, 130, 246, 0.1)', color: 'rgb(59, 130, 246)', borderRadius: '8px' }}>
            <User size={20} />
          </div>
          <h2 className="text-xl font-semibold m-0">Profile Details</h2>
        </div>
        
        {profileMessage.text && (
          <div style={{ padding: '0.75rem', borderRadius: '8px', background: profileMessage.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)', border: '1px solid ' + (profileMessage.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'), color: profileMessage.type === 'error' ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)', fontSize: '0.875rem' }}>
            {profileMessage.text}
          </div>
        )}

        <form onSubmit={handleProfileUpdate} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label style={{ fontSize: '0.875rem', fontWeight: 500 }}>Email Address</label>
            <input type="email" value={user?.email || ''} disabled className="input-field w-full opacity-60 cursor-not-allowed" />
          </div>
          
          <div className="flex gap-4">
            <div className="flex flex-col gap-1.5 flex-1">
              <label htmlFor="editFirstName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>First Name</label>
              <input id="editFirstName" type="text" className="input-field w-full" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5 flex-1">
              <label htmlFor="editLastName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Last Name</label>
              <input id="editLastName" type="text" className="input-field w-full" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>

          <button type="submit" disabled={profileLoading} className="btn btn-primary mt-2 flex items-center justify-center gap-2 self-start" style={{ padding: '0.75rem 1.5rem' }}>
            <Save size={16} /> Save Changes
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProfileGeneral;
