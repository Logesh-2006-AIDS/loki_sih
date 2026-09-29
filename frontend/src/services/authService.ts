import api from './api';
import { UserProfile } from '../types/scheme';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export const authService = {
  async login(email: string, password: string): Promise<UserProfile> {
    const res = await api.post<LoginResponse>('/auth/login', {
      email: email.trim(),
      password,
    });
    localStorage.setItem('token', res.data.access_token);
    localStorage.setItem('user', JSON.stringify(res.data.user));
    window.dispatchEvent(new Event('auth-changed'));
    return res.data.user;
  },

  async fetchCurrentUser(): Promise<UserProfile | null> {
    if (!this.isAuthenticated()) return null;
    try {
      const res = await api.get<UserProfile>('/auth/me');
      localStorage.setItem('user', JSON.stringify(res.data));
      return res.data;
    } catch {
      this.logout();
      return null;
    }
  },

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event('auth-changed'));
  },

  getCurrentUser(): UserProfile | null {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr) as UserProfile;
    } catch {
      return null;
    }
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  },

  async registerApplicant(data: {
    full_name: string;
    email: string;
    phone: string;
    password: string;
  }): Promise<UserProfile> {
    const res = await api.post<UserProfile>('/auth/register', data);
    return res.data;
  },

  async registerStaff(data: {
    full_name: string;
    email: string;
    phone: string;
    password: string;
    requested_role: 'OFFICER' | 'COMMITTEE';
    employee_id: string;
    department: string;
    designation: string;
    jurisdiction: string;
  }): Promise<UserProfile> {
    const res = await api.post<UserProfile>('/auth/register-staff', data);
    return res.data;
  },
};

