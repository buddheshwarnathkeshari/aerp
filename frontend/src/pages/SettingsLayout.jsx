import React from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { User, Lock, Link as LinkIcon } from 'lucide-react';

const SettingsLayout = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <div className="flex animate-fade-in" style={{ gap: '2rem', alignItems: 'flex-start', width: '100%' }}>
      
      {/* Sidebar Navigation */}
      <aside className="glass-panel flex-col" style={{ width: '250px', flexShrink: 0, padding: '1.5rem', gap: '0.5rem' }}>
        <h2 style={{ fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', color: 'var(--text-secondary)', paddingLeft: '0.75rem' }}>Settings</h2>
        
        <Link 
          to="/profile" 
          className="dropdown-item flex items-center"
          style={{ 
            textDecoration: 'none', 
            color: 'var(--text-primary)',
            padding: '0.75rem',
            borderRadius: '8px',
            gap: '0.75rem',
            backgroundColor: currentPath === '/profile' ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
          }}
        >
          <User size={18} />
          General Info
        </Link>
        
        <Link 
          to="/profile/security" 
          className="dropdown-item flex items-center"
          style={{ 
            textDecoration: 'none', 
            color: 'var(--text-primary)',
            padding: '0.75rem',
            borderRadius: '8px',
            gap: '0.75rem',
            backgroundColor: currentPath === '/profile/security' ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
          }}
        >
          <Lock size={18} />
          Security
        </Link>
        
        <Link 
          to="/profile/connectors" 
          className="dropdown-item flex items-center"
          style={{ 
            textDecoration: 'none', 
            color: 'var(--text-primary)',
            padding: '0.75rem',
            borderRadius: '8px',
            gap: '0.75rem',
            backgroundColor: currentPath === '/profile/connectors' ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
          }}
        >
          <LinkIcon size={18} />
          Connectors
        </Link>
      </aside>

      {/* Main Content Area */}
      <div style={{ flex: 1 }}>
        <Outlet />
      </div>
      
    </div>
  );
};

export default SettingsLayout;
