import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import PowerBIEmbed from '../pages/PowerBIEmbed';
import { withProviders } from '../tests/TestProviders';

vi.mock('../api/client', () => ({
  apiGet: vi.fn(),
  setAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
  authVerifyToken: vi.fn(),
  authLogin: vi.fn(),
}));

test('renders the embed iframe', async () => {
  const { apiGet } = await import('../api/client');
  
  vi.mocked(apiGet).mockResolvedValue({
    ok: true,
    url: 'https://app.powerbi.com/test-embed-url'
  });

  render(withProviders(<PowerBIEmbed />));
  
  await waitFor(() => {
    const frame = screen.getByTitle(/Power BI Dashboard/i);
    expect(frame).toBeInTheDocument();
    expect(frame).toHaveAttribute('src', 'https://app.powerbi.com/test-embed-url');
  }, { timeout: 3000 });
});

test('shows loading state initially', async () => {
  const { apiGet } = await import('../api/client');
  
  vi.mocked(apiGet).mockImplementation(() => new Promise(() => {}));
  
  render(withProviders(<PowerBIEmbed />));
  expect(screen.getByText(/Loading/i)).toBeInTheDocument();
});

test('shows error when API fails', async () => {
  const { apiGet } = await import('../api/client');
  
  vi.mocked(apiGet).mockRejectedValue(new Error('API Error'));

  render(withProviders(<PowerBIEmbed />));
  
  await waitFor(() => {
    expect(screen.getByText(/Failed to load Power BI/i)).toBeInTheDocument();
  }, { timeout: 3000 });
});
