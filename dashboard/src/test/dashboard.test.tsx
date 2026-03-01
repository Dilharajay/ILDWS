import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginView from '../views/LoginView'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('LoginView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    mockNavigate.mockClear()
  })

  it('renders login form with ILEWS branding', () => {
    render(
      <MemoryRouter>
        <LoginView />
      </MemoryRouter>
    )
    expect(screen.getByText('ILEWS')).toBeInTheDocument()
    expect(screen.getByText('Landslide Early Warning System')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('operator@ilews.gov')).toBeInTheDocument()
    expect(screen.getByText('Sign In')).toBeInTheDocument()
  })

  it('has email and password fields', () => {
    render(
      <MemoryRouter>
        <LoginView />
      </MemoryRouter>
    )
    const emailInput = screen.getByPlaceholderText('operator@ilews.gov')
    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toBeRequired()

    const passwordInput = document.querySelector('input[type="password"]')
    expect(passwordInput).toBeInTheDocument()
  })
})

describe('AuthStore', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('initializes with no auth', async () => {
    const { useAuthStore } = await import('../store/authStore')
    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(false)
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
  })

  it('logout clears session', async () => {
    sessionStorage.setItem('ilews_token', 'test-token')
    const { useAuthStore } = await import('../store/authStore')
    useAuthStore.getState().logout()
    expect(sessionStorage.getItem('ilews_token')).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})

describe('API Client', () => {
  it('creates axios instance with correct config', async () => {
    const { apiClient } = await import('../api/client')
    expect(apiClient.defaults.timeout).toBe(15000)
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })
})
