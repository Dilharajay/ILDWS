import { create } from 'zustand';
import { apiClient } from '../api/client';
import type { User, TokenResponse } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: sessionStorage.getItem('ilews_token'),
  isAuthenticated: !!sessionStorage.getItem('ilews_token'),
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await apiClient.post<TokenResponse>(
        '/v1/auth/token',
        formData,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );

      const { access_token } = response.data;
      sessionStorage.setItem('ilews_token', access_token);

      // Fetch user profile
      const userResponse = await apiClient.get<{ status: string; data: User }>(
        '/v1/users/me',
        { headers: { Authorization: `Bearer ${access_token}` } }
      );

      set({
        token: access_token,
        user: userResponse.data.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message || 'Login failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    sessionStorage.removeItem('ilews_token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  refreshToken: async () => {
    const { token } = get();
    if (!token) return;
    try {
      const response = await apiClient.post<TokenResponse>(
        '/v1/auth/refresh',
        { refresh_token: token }
      );
      const { access_token } = response.data;
      sessionStorage.setItem('ilews_token', access_token);
      set({ token: access_token });
    } catch {
      get().logout();
    }
  },

  setUser: (user: User) => set({ user }),
}));
