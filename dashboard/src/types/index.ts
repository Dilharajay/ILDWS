export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export interface Slope {
  id: string;
  name: string;
  location_description: string;
  latitude: number;
  longitude: number;
  risk_level: RiskLevel;
  risk_score: number;
}

export type RiskLevel = 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED';

export interface SensorNode {
  node_id: string;
  slope_id: string;
  slope_name?: string;
  name: string;
  latitude: number;
  longitude: number;
  status: 'active' | 'inactive' | 'maintenance' | 'offline';
  battery_voltage: number;
  firmware_version: string;
  last_seen: string;
  risk_level: RiskLevel;
  risk_score: number;
}

export interface SensorReading {
  id: string;
  node_id: string;
  timestamp: string;
  soil_moisture_10cm: number;
  soil_moisture_30cm: number;
  soil_moisture_60cm: number;
  rainfall_mm: number;
  tilt_x: number;
  tilt_y: number;
  vibration_peak_g: number;
  battery_voltage: number;
}

export interface Alert {
  alert_id: string;
  slope_id: string;
  slope_name?: string;
  risk_level: RiskLevel;
  risk_score: number;
  triggered_at: string;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  message: string;
}

export interface RiskZone {
  slope_id: string;
  slope_name: string;
  risk_level: RiskLevel;
  risk_score: number;
  boundary: [number, number][];
}

export interface MapData {
  nodes: SensorNode[];
  risk_zones: RiskZone[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  status: 'error';
  error: {
    code: string;
    message: string;
  };
}

export interface WSEvent {
  type: 'RISK_UPDATE' | 'ALERT_TRIGGERED' | 'NODE_STATUS_CHANGE';
  data: Record<string, unknown>;
  timestamp: string;
}
