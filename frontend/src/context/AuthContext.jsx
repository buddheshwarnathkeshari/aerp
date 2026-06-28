import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      localStorage.setItem('access_token', token);
      fetchCurrentUser();
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setIsLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async (currentToken = token) => {
    if (!currentToken) {
      setIsLoading(false);  // Fix: early return must always unblock the loader
      return;
    }
    setIsLoading(true);

    // Timeout guard — if the API doesn't respond in 8s (e.g. container starting
    // up, Vite proxy hanging on a stale connection), abort and unblock the UI.
    // Without this, fetch hangs indefinitely → isLoading stays true → spinner forever.
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
      const response = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${currentToken}` },
        signal: controller.signal,
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token expired or invalid — clear it so user is sent to login
        setToken(null);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        // Timed out — API is slow/starting up. Don't clear token; user can retry.
        console.warn('Auth check timed out — API may still be starting up.');
      } else {
        console.error('Failed to fetch user:', error);
      }
    } finally {
      clearTimeout(timeout);
      setIsLoading(false);
    }
  };

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = 'Login failed';
      try {
        const error = await response.json();
        errorMsg = error.detail || errorMsg;
      } catch (e) {}
      throw new Error(errorMsg);
    }

    const data = await response.json();
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('access_token', data.access_token);
    setIsLoading(true); // Prevents premature redirect in ProtectedRoute
    setToken(data.access_token);
  };

  const register = async (email, password, firstName, lastName) => {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        first_name: firstName,
        last_name: lastName
      }),
    });

    if (!response.ok) {
      let errorMsg = 'Registration failed';
      try {
        const error = await response.json();
        errorMsg = error.detail || errorMsg;
      } catch (e) {}
      throw new Error(errorMsg);
    }
    
    // Auto login after registration
    await login(email, password);
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken && token) {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
      } catch (err) {
        console.error("Logout failed API side", err);
      }
    }
    setToken(null);
  };

  // Wrapper for authenticated fetch calls
  const authFetch = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    const response = await fetch(url, { ...options, headers });
    
    // Auto-logout if unauthorized (simple approach for now)
    if (response.status === 401) {
      setToken(null);
    }
    return response;
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout, authFetch, fetchCurrentUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
