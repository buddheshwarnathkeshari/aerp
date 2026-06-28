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
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-center cursor-pointer transition hover-brighten profile-dropdown-btn ${user?.first_name ? 'profile-dropdown-btn-with-name' : 'profile-dropdown-btn-icon-only'}`} 
      >
        {user?.first_name && (
          <span className="profile-dropdown-name">
            {user.first_name}
          </span>
        )}
        <div className={`profile-dropdown-avatar ${user?.first_name ? 'profile-dropdown-avatar-with-name' : 'profile-dropdown-avatar-icon-only'}`}>
          <User size={user?.first_name ? 16 : 20} />
        </div>
      </button>
      
      {isOpen && (
        <div className="animate-slide-up profile-dropdown-menu">
          <div className="profile-dropdown-header">
            <div className="profile-dropdown-header-name">{user?.first_name} {user?.last_name}</div>
            <div className="profile-dropdown-header-email">{user?.email}</div>
          </div>
          
          <Link to="/profile" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center">
            <Settings size={16} /> Update Profile
          </Link>
          <Link to="/profile/security" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center">
            <Key size={16} /> Change Password
          </Link>
          <Link to="/profile/connectors" onClick={() => setIsOpen(false)} className="dropdown-item flex items-center">
            <LinkIcon size={16} /> Manage Connectors
          </Link>
          <div className="dropdown-divider" />
          <button onClick={handleLogout} className="dropdown-item dropdown-item-logout flex items-center">
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
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';
  
  if (isAuthPage) return null;

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
