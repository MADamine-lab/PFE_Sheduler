// AuthContext.jsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import { login as apiLogin, logout as apiLogout, getCurrentUser } from './api';
import api from './api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      // ✅ Step 1: Always fetch CSRF token first
      try { await api.get("/auth/csrf/"); } catch {}

      // Step 2: Check if already logged in
      try {
        const response = await getCurrentUser();
        setUser(response.data);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // ✅ Fix: accept (email, password) separately to match App.jsx call
  const login = async (email, password) => {
    // ✅ Refresh CSRF token right before login POST
    try { await api.get("/auth/csrf/"); } catch {}

    const response = await apiLogin({ email, password });
    const meResponse = await getCurrentUser();
    setUser(meResponse.data);
    return meResponse.data;
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch {}
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);