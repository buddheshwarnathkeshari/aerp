import React, { useState, useRef, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import { User, Settings, Key, Link as LinkIcon, LogOut } from 'lucide-react'
import SubmitReview from './components/SubmitReview'
import ReviewDashboard from './components/ReviewDashboard'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import SettingsLayout from './pages/SettingsLayout'
import ProfileGeneral from './pages/ProfileGeneral'
import ProfileSecurity from './pages/ProfileSecurity'
import ProfileConnectors from './pages/ProfileConnectors'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider, useAuth } from './context/AuthContext'

const ProfileDropdown = () => {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    setIsOpen(false);
  };

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-center cursor-pointer transition hover-brighten" 
        style={{ 
          height: '40px', 
          padding: user?.first_name ? '0 0.25rem 0 1rem' : '0',
          width: user?.first_name ? 'auto' : '40px',
          gap: '0.5rem', 
          borderRadius: '2rem', 
          background: 'var(--bg-tertiary)', 
          color: 'var(--text-primary)', 
          border: '1px solid rgba(255,255,255,0.1)' 
        }}>
        {user?.first_name && (
          <span style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
            {user.first_name}
          </span>
        )}
        <div style={{ 
          width: user?.first_name ? '32px' : '100%', 
          height: user?.first_name ? '32px' : '100%', 
          borderRadius: '50%', 
          background: user?.first_name ? 'rgba(255,255,255,0.05)' : 'transparent', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center' 
        }}>
          <User size={user?.first_name ? 16 : 20} />
        </div>
      </button>
      
      {isOpen && (
        <div className="animate-slide-up" style={{ 
          position: 'absolute', 
          top: '100%', 
          right: 0, 
          marginTop: '0.75rem',
          minWidth: '240px',
          padding: '0.5rem',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          backgroundColor: 'rgba(10, 15, 28, 0.95)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(255,255,255,0.15)',
          borderTop: '1px solid rgba(255,255,255,0.25)',
          borderRadius: '12px',
          boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.8), 0 0 20px rgba(59, 130, 246, 0.1)'
        }}>
          <div style={{ padding: '0.75rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '8px' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{user?.first_name} {user?.last_name}</div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)' }}>{user?.email}</div>
          </div>
          
          <Link to="/profile" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center" style={{ padding: '0.5rem', borderRadius: '6px', color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.875rem', gap: '0.75rem' }}>
            <Settings size={16} /> Update Profile
          </Link>
          <Link to="/profile/security" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center" style={{ padding: '0.5rem', borderRadius: '6px', color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.875rem', gap: '0.75rem' }}>
            <Key size={16} /> Change Password
          </Link>
          <Link to="/profile/connectors" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center" style={{ padding: '0.5rem', borderRadius: '6px', color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.875rem', gap: '0.75rem' }}>
            <LinkIcon size={16} /> Manage Connectors
          </Link>
          <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '4px 0' }} />
          <button onClick={handleLogout} className="dropdown-item flex items-center" style={{ padding: '0.5rem', borderRadius: '6px', color: '#ef4444', textDecoration: 'none', fontSize: '0.875rem', background: 'transparent', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer', gap: '0.75rem' }}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      )}
    </div>
  )
}

const HeaderNavigation = () => {
  const { user } = useAuth();
  const location = useLocation();
  
  return (
    <nav className="flex items-center gap-4">
      {location.pathname !== '/' && (
        <Link to="/" className="btn btn-primary" style={{ textDecoration: 'none' }}>+ New Review</Link>
      )}
      {user ? (
        <ProfileDropdown />
      ) : (
        <Link to="/login" className="btn glass-panel" style={{ textDecoration: 'none' }}>Login</Link>
      )}
    </nav>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <header style={{ 
          width: '100%',
          padding: '1rem 2rem',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          background: 'rgba(10, 15, 28, 0.85)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 4px 30px rgba(0, 0, 0, 0.5)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
              <img src="/logo-full.png" alt="AERP" style={{ height: '32px', objectFit: 'contain' }} />
            </Link>
            <HeaderNavigation />
          </div>
        </header>

        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected Routes */}
            <Route path="/" element={<ProtectedRoute><SubmitReview /></ProtectedRoute>} />
            <Route path="/review/:id" element={<ProtectedRoute><ReviewDashboard /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><SettingsLayout /></ProtectedRoute>}>
              <Route index element={<ProfileGeneral />} />
              <Route path="security" element={<ProfileSecurity />} />
              <Route path="connectors" element={<ProfileConnectors />} />
            </Route>
          </Routes>
        </main>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
