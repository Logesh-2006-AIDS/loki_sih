import api from './api';
import { UserProfile } from '../types/scheme';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export const DEMO_CREDENTIALS: Record<string, { email: string; roleName: string }> = {
  APPLICANT: { email: 'applicant@demo.gov.in', roleName: 'Tribal Applicant' },
  OFFICER: { email: 'officer@demo.gov.in', roleName: 'Verification Officer' },
  COMMITTEE: { email: 'committee@demo.gov.in', roleName: 'Selection Committee' },
  ADMIN: { email: 'admin@demo.gov.in', roleName: 'System Administrator' },
};

export const authService = {
  async login(email: string, password = 'Demo@12345'): Promise<UserProfile> {
    const res = await api.post<LoginResponse>('/auth/login', {
      email,
      password,
    });
    localStorage.setItem('token', res.data.access_token);
    localStorage.setItem('user', JSON.stringify(res.data.user));
    return res.data.user;
  },

  async demoLogin(role: 'APPLICANT' | 'OFFICER' | 'COMMITTEE' | 'ADMIN'): Promise<UserProfile> {
    const creds = DEMO_CREDENTIALS[role];
    return this.login(creds.email, 'Demo@12345');
  },

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
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
};
