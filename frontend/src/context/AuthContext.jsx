import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  googleLogin as apiGoogleLogin,
  emailLogin as apiEmailLogin,
  registerUser as apiRegisterUser,
  fetchCurrentUser
} from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('docmind_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('docmind_access_token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (accessToken) {
        try {
          const userData = await fetchCurrentUser();
          setUser(userData);
          localStorage.setItem('docmind_user', JSON.stringify(userData));
        } catch (err) {
          console.error("Session restoration failed:", err);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();

    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener('docmind_unauthorized', handleUnauthorized);
    return () => window.removeEventListener('docmind_unauthorized', handleUnauthorized);
  }, []);

  const setAuthSession = (access, refresh, loggedUser) => {
    setAccessToken(access);
    setUser(loggedUser);
    localStorage.setItem('docmind_access_token', access);
    localStorage.setItem('docmind_refresh_token', refresh);
    localStorage.setItem('docmind_user', JSON.stringify(loggedUser));
  };

  const loginWithGoogleToken = async (credential) => {
    try {
      const data = await apiGoogleLogin(credential);
      const { access, refresh, user: loggedUser } = data;
      setAuthSession(access, refresh, loggedUser);
      return { success: true, user: loggedUser };
    } catch (error) {
      console.error("Google login error:", error);
      const errMsg = error.response?.data?.error || "Google Authentication failed.";
      return { success: false, error: errMsg };
    }
  };

  const loginWithEmail = async (email, password) => {
    try {
      const data = await apiEmailLogin(email, password);
      const { access, refresh, user: loggedUser } = data;
      setAuthSession(access, refresh, loggedUser);
      return { success: true, user: loggedUser };
    } catch (error) {
      console.error("Email login error:", error);
      const errMsg = error.response?.data?.error || "Login failed. Please check your email and password.";
      return { success: false, error: errMsg };
    }
  };

  const registerWithEmail = async (email, password, name = '') => {
    try {
      const data = await apiRegisterUser(email, password, name);
      const { access, refresh, user: loggedUser } = data;
      setAuthSession(access, refresh, loggedUser);
      return { success: true, user: loggedUser };
    } catch (error) {
      console.error("Registration error:", error);
      const errMsg = error.response?.data?.error || "Registration failed. Please try again.";
      return { success: false, error: errMsg };
    }
  };

  const logout = () => {
    setAccessToken(null);
    setUser(null);
    localStorage.removeItem('docmind_access_token');
    localStorage.removeItem('docmind_refresh_token');
    localStorage.removeItem('docmind_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: !!accessToken && !!user,
        loading,
        loginWithGoogleToken,
        loginWithEmail,
        registerWithEmail,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
