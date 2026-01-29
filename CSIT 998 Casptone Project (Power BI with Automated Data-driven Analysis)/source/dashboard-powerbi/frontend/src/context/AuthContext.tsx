/**
 * Authentication Context Provider
 * 
 * Manages global authentication state with localStorage persistence
 * and "Remember Me" functionality.
 * 
 * @module AuthContext
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { AuthState, UserRole } from '../types';
import { setAuthToken, clearAuthToken, authVerifyToken } from '../api/client';

interface AuthContextValue extends AuthState {
  login: (username: string, role: UserRole, token?: string, rememberMe?: boolean) => void;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const defaultState: AuthState = {
  isAuthenticated: false,
  username: null,
  role: null,
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'app_auth_state_v1';
const REMEMBER_ME_KEY = 'remember_me';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Initialize state from localStorage if available, with error recovery
  const [state, setState] = useState<AuthState>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) as AuthState : defaultState;
    } catch {
      return defaultState;
    }
  });

  // Track initialization phase to prevent flash of login screen
  const [isChecking, setIsChecking] = useState(true);

  // Persist auth state changes to localStorage for page refresh survival
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const checkAuth = async (): Promise<boolean> => {
    try {
      const result = await authVerifyToken();
      if (result.ok && result.valid) {
        setState({
          isAuthenticated: true,
          username: result.user.username,
          role: result.user.role as UserRole,
        });
        return true;
      } else {
        setState(defaultState);
        clearAuthToken();
        return false;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setState(defaultState);
      clearAuthToken();
      return false;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const rememberMe = localStorage.getItem(REMEMBER_ME_KEY) === 'true';
      
      if (rememberMe && state.isAuthenticated) {
        const isValid = await checkAuth();
        if (!isValid) {
          setState(defaultState);
          localStorage.removeItem(REMEMBER_ME_KEY);
        }
      } else {
        setState(defaultState);
        clearAuthToken();
      }
      
      setIsChecking(false);
    };
    initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = (username: string, role: UserRole, token?: string, rememberMe?: boolean) => {
    if (token) {
      setAuthToken(token);
    }
    
    if (rememberMe) {
      localStorage.setItem(REMEMBER_ME_KEY, 'true');
    } else {
      localStorage.removeItem(REMEMBER_ME_KEY);
    }
    
    setState({ isAuthenticated: true, username, role });
  };

  const logout = () => {
    setState(defaultState);
    clearAuthToken();
    localStorage.removeItem(REMEMBER_ME_KEY);
  };

  // Memoize context value to prevent unnecessary re-renders of consumers
  const value = useMemo<AuthContextValue>(() => ({
    ...state,
    login,
    logout,
    checkAuth,
  }), [state]);

  // Prevent flash of login screen while verifying stored token
  if (isChecking) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>Loading...</div>;
  }

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}


