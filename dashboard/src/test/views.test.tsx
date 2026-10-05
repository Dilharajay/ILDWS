import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock apiClient
vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { data: [], meta: {} } }),
    patch: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    defaults: { timeout: 15000, headers: { 'Content-Type': 'application/json' } },
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

import AlertsView from '../views/AlertsView'
import NodesView from '../views/NodesView'
import ReportsView from '../views/ReportsView'

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AlertsView', () => {
  it('renders alert page title and filters', () => {
    render(<AlertsView />, { wrapper })
    expect(screen.getByText('Alerts')).toBeInTheDocument()
    // Shows loading state initially
    expect(screen.getByText('Loading alerts...')).toBeInTheDocument()
  })

  it('shows level and status filter dropdowns', () => {
    render(<AlertsView />, { wrapper })
    const selects = screen.getAllByRole('combobox')
    expect(selects.length).toBeGreaterThanOrEqual(2)
  })
})

describe('NodesView', () => {
  it('renders search input and title', () => {
    render(<NodesView />, { wrapper })
    expect(screen.getByText('Sensor Nodes')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Search nodes...')).toBeInTheDocument()
    // Shows loading state initially
    expect(screen.getByText('Loading nodes...')).toBeInTheDocument()
  })
})

describe('ReportsView', () => {
  it('renders reports view with type filter', () => {
    render(<ReportsView />, { wrapper })
    expect(screen.getByText('Reports')).toBeInTheDocument()
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
  })
})
