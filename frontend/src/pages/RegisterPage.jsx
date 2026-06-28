import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus } from 'lucide-react';

const RegisterPage = () => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, password, firstName, lastName);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Failed to register');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center w-full px-4" style={{ minHeight: 'calc(100vh - 80px)' }}>
      <div style={{ position: 'relative', width: '100%', maxWidth: '28rem' }}>
        {/* Dual Glow Orb */}
        <div style={{ 
          position: 'absolute', top: '-15%', left: '-15%', right: '-15%', bottom: '-15%',
          background: 'radial-gradient(circle at top left, rgba(59,130,246,0.3) 0%, transparent 50%), radial-gradient(circle at bottom right, rgba(139,92,246,0.25) 0%, transparent 50%)',
          filter: 'blur(60px)', zIndex: 0 
        }} />
        
        <div className="glass-panel w-full flex flex-col relative" style={{ padding: '3rem 2.5rem', gap: '2rem', animation: 'slideUp 0.5s ease-out forwards', zIndex: 1 }}>
          <div className="text-center flex flex-col items-center gap-2">
            <img src="/logo-full.png" alt="AERP" style={{ height: '56px', objectFit: 'contain', marginBottom: '0.5rem' }} />
            <h2 className="text-2xl font-bold m-0" style={{ background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Create an Account</h2>
            <p className="text-sm m-0" style={{ color: 'var(--text-secondary)' }}>Get started with AERP today</p>
          </div>

          {error && (
          <div style={{ padding: '0.75rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'rgb(239, 68, 68)', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex gap-4">
            <div className="flex flex-col gap-1.5 flex-1">
              <label htmlFor="firstName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>First Name</label>
              <input
                id="firstName"
                type="text"
                className="input-field w-full"
                placeholder="John"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5 flex-1">
              <label htmlFor="lastName" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Last Name</label>
              <input
                id="lastName"
                type="text"
                className="input-field w-full"
                placeholder="Doe"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Email Address</label>
            <input
              id="email"
              type="email"
              required
              className="input-field w-full"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" style={{ fontSize: '0.875rem', fontWeight: 500 }}>Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              className="input-field w-full"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary mt-2 flex justify-center items-center gap-2 w-full"
            disabled={loading}
            style={{ padding: '0.875rem' }}
          >
            {loading ? (
              <div style={{ width: '20px', height: '20px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            ) : (
              <>
                <UserPlus size={20} />
                Sign Up
              </>
            )}
          </button>
        </form>

        <p className="text-center text-sm m-0" style={{ color: 'var(--text-secondary)' }}>
          Already have an account? <Link to="/login" style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>Log in</Link>
        </p>
      </div>
      </div>
    </div>
  );
};

export default RegisterPage;
