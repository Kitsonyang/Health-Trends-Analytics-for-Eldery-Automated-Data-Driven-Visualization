import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../context/AuthContext';


function TestComponent() {
  const { isAuthenticated, username, role, login, logout } = useAuth();

  return (
    <div>
      <div data-testid="auth">{String(isAuthenticated)}</div>
      <div data-testid="user">{username ?? ''}</div>
      <div data-testid="role">{role ?? ''}</div>
      <button onClick={() => login('donald', 'admin')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  test('initial state is unauthenticated', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('');
    expect(screen.getByTestId('role')).toHaveTextContent('');
  });

  test('login updates context values', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await user.click(screen.getByText('Login'));

    expect(screen.getByTestId('auth')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('donald');
    expect(screen.getByTestId('role')).toHaveTextContent('admin');
  });

  test('logout resets context values', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await user.click(screen.getByText('Login'));
    await user.click(screen.getByText('Logout'));

    expect(screen.getByTestId('auth')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('');
    expect(screen.getByTestId('role')).toHaveTextContent('');
  });
});