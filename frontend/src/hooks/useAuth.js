import { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';

export const useAuth = () => {
  const [authState, setAuthState] = useState({
    isAuthenticated: null, // null = checking, true/false = known
    user: null,
    loading: true
  });

  const checkAuth = async () => {
    try {
      const data = await apiClient.get('/auth/auth-status');
      setAuthState({
        isAuthenticated: true,
        user: data.user,
        loading: false
      });
    } catch (error) {
      setAuthState({
        isAuthenticated: false,
        user: null,
        loading: false
      });
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return { ...authState, checkAuth };
};
