export type UserRole = 'user' | 'admin';

export interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: UserRole | null;
}


