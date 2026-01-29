import '@testing-library/jest-dom';
import { vi } from 'vitest';

import { TextEncoder, TextDecoder } from 'node:util';
if (!globalThis.TextEncoder) (globalThis as any).TextEncoder = TextEncoder;
if (!globalThis.TextDecoder) (globalThis as any).TextDecoder = TextDecoder as unknown as typeof globalThis.TextDecoder;

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), 
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

global.fetch = vi.fn();

