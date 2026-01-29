import React, { useEffect } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { vi } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';
import ProtectedRoute from '../routes/ProtectedRoute';

function LoginPage() { return <div data-testid="login-page">Login</div>; }
function HomePage() { return <div data-testid="home">Home</div>; }
function SecurePage() { return <div data-testid="secure">Top Secret</div>; }

function LoginAs({ username, role, children }:{
  username: string; role: 'admin' | 'user'; children?: React.ReactNode;
}) {
  const { login } = useAuth();
  useEffect(() => { login(username, role); }, []);
  return <>{children}</>;
}
function App({ preauth }: { preauth?: { user: string; role: 'admin'|'user'; to: string } }) {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<HomePage />} />
      {preauth && (
        <Route
          path="/preauth"
          element={
            <LoginAs username={preauth.user} role={preauth.role}>
              <Navigate to={preauth.to} replace />
            </LoginAs>
          }
        />
      )}
      <Route element={<ProtectedRoute roles={['admin']} />}>
        <Route path="/app" element={<SecurePage />} />
      </Route>
    </Routes>
  );
}
function renderApp(start: string, preauth?: { user: string; role: 'admin'|'user'; to: string }) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[start]}>
        <App preauth={preauth} />
      </MemoryRouter>
    </AuthProvider>
  );
}
afterEach(() => {
  vi.clearAllMocks();
  vi.clearAllTimers?.();
});

test('redirects unauthenticated users to /login and hides secure content', async () => {
  renderApp('/app');
  expect(await screen.findByTestId('login-page')).toBeInTheDocument();
  expect(screen.queryByTestId('secure')).toBeNull();
});

test('allows access when authenticated with required role (admin)', async () => {
  renderApp('/preauth', { user: 'alice', role: 'admin', to: '/app' });
  expect(await screen.findByTestId('secure')).toBeInTheDocument();
  expect(screen.queryByTestId('login-page')).toBeNull();
});

test('blocks/redirects when authenticated with wrong role', async () => {
  renderApp('/preauth', { user: 'bob', role: 'user', to: '/app' });
  expect(await screen.findByTestId('home')).toBeInTheDocument();
  expect(screen.queryByTestId('secure')).toBeNull();
});
