import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock } from 'lucide-react';

const ProfileSecurity = () => {
  const { authFetch } = useAuth();

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState({ text: '', type: '' });
  const [passwordLoading, setPasswordLoading] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordLoading(true);
    setPasswordMessage({ text: '', type: '' });
    
    try {
      const response = await authFetch('/api/v1/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to change password');
      }
      
      setPasswordMessage({ text: 'Password changed successfully!', type: 'success' });
      setOldPassword('');
      setNewPassword('');
    } catch (err) {
      setPasswordMessage({ text: err.message, type: 'error' });
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold m-0 tracking-tight">Security</h1>
        <p className="text-sm m-0 mt-1" style={{ color: 'var(--text-secondary)' }}>Update your password and secure your account.</p>
      </div>

      <div className="glass-panel p-6 flex flex-col gap-6">
        <div className="flex items-center gap-3 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
          <div style={{ padding: '0.5rem', background: 'rgba(168, 85, 247, 0.1)', color: 'rgb(168, 85, 247)', borderRadius: '8px' }}>
            <Lock size={20} />
          </div>
          <h2 className="text-xl font-semibold m-0">Change Password</h2>
        </div>
        
        {passwordMessage.text && (
          <div style={{ padding: '0.75rem', borderRadius: '8px', background: passwordMessage.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)', border: '1px solid ' + (passwordMessage.type === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'), color: passwordMessage.type === 'error' ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)', fontSize: '0.875rem' }}>
            {passwordMessage.text}
          </div>
        )}

        <form onSubmit={handlePasswordChange} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="oldPassword" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Current Password</label>
            <input id="oldPassword" type="password" required minLength={8} className="input-field w-full" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="newPassword" style={{ fontSize: '0.875rem', fontWeight: 500 }}>New Password</label>
            <input id="newPassword" type="password" required minLength={8} className="input-field w-full" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </div>

          <button type="submit" disabled={passwordLoading} className="btn btn-primary mt-2 flex items-center justify-center gap-2 self-start" style={{ padding: '0.75rem 1.5rem', background: 'var(--accent-secondary)' }}>
            <Lock size={16} /> Update Password
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProfileSecurity;
