import { describe, it, expect, beforeEach } from 'vitest'
import { useMapStore } from '../store/mapStore'
import { useAlertStore } from '../store/alertStore'
import type { SensorNode, Alert, RiskZone } from '../types'

const mockNode: SensorNode = {
  node_id: 'NODE-001',
  slope_id: 'SLP-001',
  slope_name: 'Test Slope',
  name: 'Test Node',
  latitude: 3.1,
  longitude: 101.7,
  status: 'active',
  battery_voltage: 3.7,
  firmware_version: '1.0.0',
  last_seen: new Date().toISOString(),
  risk_level: 'GREEN',
  risk_score: 0.2,
}

const mockAlert: Alert = {
  alert_id: 'ALT-2024-000001',
  slope_id: 'SLP-001',
  slope_name: 'Test Slope',
  risk_level: 'RED',
  risk_score: 0.92,
  triggered_at: new Date().toISOString(),
  status: 'active',
  message: 'Critical risk detected',
}

describe('MapStore', () => {
  beforeEach(() => {
    useMapStore.setState({ nodes: new Map(), riskZones: new Map() })
  })

  it('sets nodes from array', () => {
    useMapStore.getState().setNodes([mockNode])
    expect(useMapStore.getState().nodes.size).toBe(1)
    expect(useMapStore.getState().nodes.get('NODE-001')?.risk_level).toBe('GREEN')
  })

  it('updates node risk level', () => {
    useMapStore.getState().setNodes([mockNode])
    useMapStore.getState().updateNodeRisk('NODE-001', 'RED', 0.95)
    const node = useMapStore.getState().nodes.get('NODE-001')
    expect(node?.risk_level).toBe('RED')
    expect(node?.risk_score).toBe(0.95)
  })

  it('sets risk zones', () => {
    const zone: RiskZone = {
      slope_id: 'SLP-001',
      slope_name: 'Test Slope',
      risk_level: 'ORANGE',
      risk_score: 0.75,
      boundary: [[3.1, 101.7], [3.2, 101.8], [3.1, 101.8]],
    }
    useMapStore.getState().setRiskZones([zone])
    expect(useMapStore.getState().riskZones.size).toBe(1)
  })
})

describe('AlertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({ activeAlerts: [], alertHistory: [] })
  })

  it('adds alert to active alerts', () => {
    useAlertStore.getState().addAlert(mockAlert)
    expect(useAlertStore.getState().activeAlerts).toHaveLength(1)
    expect(useAlertStore.getState().activeAlerts[0].alert_id).toBe('ALT-2024-000001')
  })

  it('acknowledges alert', () => {
    useAlertStore.getState().addAlert(mockAlert)
    useAlertStore.getState().acknowledgeAlert('ALT-2024-000001')
    expect(useAlertStore.getState().activeAlerts[0].status).toBe('acknowledged')
  })

  it('clears alert moves to history', () => {
    useAlertStore.getState().addAlert(mockAlert)
    useAlertStore.getState().clearAlert('ALT-2024-000001')
    expect(useAlertStore.getState().activeAlerts).toHaveLength(0)
    expect(useAlertStore.getState().alertHistory).toHaveLength(1)
  })

  it('setAlerts splits by status', () => {
    const resolved: Alert = { ...mockAlert, alert_id: 'ALT-2', status: 'resolved' }
    useAlertStore.getState().setAlerts([mockAlert, resolved])
    expect(useAlertStore.getState().activeAlerts).toHaveLength(1)
    expect(useAlertStore.getState().alertHistory).toHaveLength(1)
  })
})
