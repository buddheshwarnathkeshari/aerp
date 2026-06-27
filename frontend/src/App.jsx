import React, { useState, useRef, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Activity, User, Settings, Key, Link as LinkIcon, LogOut } from 'lucide-react'
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
        className="flex items-center justify-center cursor-pointer transition" 
        style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <User size={20} />
      </button>
      
      {isOpen && (
        <div className="glass-panel animate-slide-up" style={{ 
          position: 'absolute', 
          top: '100%', 
          right: 0, 
          marginTop: '0.5rem',
          minWidth: '220px',
          padding: '0.5rem',
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ padding: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)', marginBottom: '4px' }}>
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
  
  return (
    <nav className="flex items-center gap-4">
      <Link to="/" className="btn btn-primary" style={{ textDecoration: 'none' }}>+ New Review</Link>
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
        <header className="glass-panel" style={{ borderRadius: 0, borderTop: 'none', borderLeft: 'none', borderRight: 'none', padding: '1rem 2rem', position: 'relative', zIndex: 100 }}>
          <div className="container flex items-center justify-between" style={{ padding: 0 }}>
            <Link to="/" className="flex items-center gap-2" style={{ textDecoration: 'none', color: 'var(--text-primary)' }}>
              <div style={{ padding: '0.5rem', background: 'var(--accent-primary)', borderRadius: '8px', display: 'flex' }}>
                <Activity size={24} color="white" />
              </div>
              <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>AERP</h1>
            </Link>
            <HeaderNavigation />
          </div>
        </header>

        <main className="container flex-col" style={{ flex: 1 }}>
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
