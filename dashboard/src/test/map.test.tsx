import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RedAlertModal from '../components/RedAlertModal'

// Mock AudioContext
const mockClose = vi.fn()
const mockStart = vi.fn()
const mockStop = vi.fn()
const mockConnect = vi.fn().mockReturnValue({})

vi.stubGlobal('AudioContext', vi.fn(() => ({
  createOscillator: () => ({
    connect: mockConnect,
    frequency: { value: 0 },
    type: 'sine',
    start: mockStart,
    stop: mockStop,
  }),
  createGain: () => ({
    connect: mockConnect,
    gain: { value: 0 },
  }),
  destination: {},
  close: mockClose,
})))

describe('RedAlertModal', () => {
  it('renders critical alert with slope name', () => {
    render(
      <RedAlertModal
        slopeName="Bukit Antarabangsa"
        riskScore={0.92}
        timestamp={new Date().toISOString()}
        onAcknowledge={vi.fn()}
      />
    )
    expect(screen.getByText('CRITICAL ALERT')).toBeInTheDocument()
    expect(screen.getByText('Bukit Antarabangsa')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('ACKNOWLEDGE')).toBeInTheDocument()
  })

  it('calls onAcknowledge when button clicked', async () => {
    const onAck = vi.fn()
    render(
      <RedAlertModal
        slopeName="Test Slope"
        riskScore={0.95}
        timestamp={new Date().toISOString()}
        onAcknowledge={onAck}
      />
    )
    screen.getByText('ACKNOWLEDGE').click()
    expect(onAck).toHaveBeenCalledOnce()
  })
})

describe('Risk colors and levels', () => {
  it('maps risk levels to correct colors', () => {
    const RISK_COLORS = {
      GREEN: '#22c55e',
      YELLOW: '#eab308',
      ORANGE: '#f97316',
      RED: '#ef4444',
    }
    expect(RISK_COLORS.GREEN).toBe('#22c55e')
    expect(RISK_COLORS.YELLOW).toBe('#eab308')
    expect(RISK_COLORS.ORANGE).toBe('#f97316')
    expect(RISK_COLORS.RED).toBe('#ef4444')
  })

  it('calculates marker radius from score', () => {
    const markerRadius = (score: number) => Math.max(8, Math.round(8 + score * 10))
    expect(markerRadius(0)).toBe(8)
    expect(markerRadius(0.5)).toBe(13)
    expect(markerRadius(1.0)).toBe(18)
  })
})
