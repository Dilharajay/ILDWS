import { X, ExternalLink } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { apiClient } from '../api/client';
import type { SensorNode, SensorReading, RiskLevel } from '../types';

const RISK_COLORS: Record<RiskLevel, string> = {
  GREEN: '#22c55e',
  YELLOW: '#eab308',
  ORANGE: '#f97316',
  RED: '#ef4444',
};

interface Props {
  node: SensorNode;
  onClose: () => void;
}

export default function NodeDetailPanel({ node, onClose }: Props) {
  const { data: readings } = useQuery<SensorReading[]>({
    queryKey: ['nodeReadings', node.node_id],
    queryFn: async () => {
      const res = await apiClient.get(
        `/v1/readings/${node.node_id}?limit=288`
      );
      return res.data.data || [];
    },
    refetchInterval: 60_000,
  });

  const riskColor = RISK_COLORS[node.risk_level] || RISK_COLORS.GREEN;
  const riskPercent = Math.round(node.risk_score * 100);

  // Use last reading for current values
  const latest = readings?.[0];

  // Format readings for sparkline (oldest to newest)
  const chartData = (readings || [])
    .slice()
    .reverse()
    .map((r) => ({
      time: new Date(r.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      soilMoisture: r.soil_moisture_30cm,
      tiltX: r.tilt_x,
      tiltY: r.tilt_y,
    }));

  return (
    <div className="w-96 bg-primary border-l border-border overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">
            {node.node_id}
          </h3>
          <p className="text-sm text-text-secondary">
            {node.slope_name || node.slope_id}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-text-secondary hover:text-text-primary"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Risk Gauge */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-text-secondary">Risk Score</span>
          <span
            className="text-2xl font-bold"
            style={{ color: riskColor }}
          >
            {riskPercent}%
          </span>
        </div>
        <div className="w-full h-3 bg-surface-dark rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${riskPercent}%`,
              backgroundColor: riskColor,
            }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-text-secondary">
          <span>0%</span>
          <span
            className="font-medium"
            style={{ color: riskColor }}
          >
            {node.risk_level}
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* Current Readings */}
      <div className="p-4 border-b border-border">
        <h4 className="text-sm font-medium text-text-secondary mb-3">
          Current Readings
        </h4>
        {latest ? (
          <table className="w-full text-sm">
            <tbody className="divide-y divide-border">
              {[
                ['Soil Moisture 10cm', `${latest.soil_moisture_10cm?.toFixed(1)}%`],
                ['Soil Moisture 30cm', `${latest.soil_moisture_30cm?.toFixed(1)}%`],
                ['Soil Moisture 60cm', `${latest.soil_moisture_60cm?.toFixed(1)}%`],
                ['Rainfall', `${latest.rainfall_mm?.toFixed(1)} mm`],
                ['Tilt X', `${latest.tilt_x?.toFixed(2)}°`],
                ['Tilt Y', `${latest.tilt_y?.toFixed(2)}°`],
                ['Battery', `${latest.battery_voltage?.toFixed(2)} V`],
              ].map(([label, value]) => (
                <tr key={label}>
                  <td className="py-1.5 text-text-secondary">{label}</td>
                  <td className="py-1.5 text-right text-text-primary font-mono">
                    {value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-text-secondary text-sm">No readings available</p>
        )}
      </div>

      {/* Sparkline Charts */}
      {chartData.length > 0 && (
        <div className="p-4 border-b border-border">
          <h4 className="text-sm font-medium text-text-secondary mb-3">
            24h Soil Moisture Trend
          </h4>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '4px',
                  color: '#f1f5f9',
                }}
              />
              <Line
                type="monotone"
                dataKey="soilMoisture"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>

          <h4 className="text-sm font-medium text-text-secondary mb-3 mt-4">
            24h Tilt Trend
          </h4>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '4px',
                  color: '#f1f5f9',
                }}
              />
              <Line
                type="monotone"
                dataKey="tiltX"
                stroke="#f97316"
                dot={false}
                strokeWidth={2}
                name="Tilt X"
              />
              <Line
                type="monotone"
                dataKey="tiltY"
                stroke="#eab308"
                dot={false}
                strokeWidth={2}
                name="Tilt Y"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Meta Info */}
      <div className="p-4 border-b border-border">
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-text-secondary">Last Seen</span>
            <span className="text-text-primary">
              {node.last_seen
                ? new Date(node.last_seen).toLocaleString()
                : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Coordinates</span>
            <span className="text-text-primary font-mono text-xs">
              {node.latitude?.toFixed(6)}, {node.longitude?.toFixed(6)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Status</span>
            <span className="text-text-primary capitalize">{node.status}</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4">
        <Link
          to={`/alerts?slope=${node.slope_id}`}
          className="flex items-center justify-center gap-2 w-full py-2 bg-accent hover:bg-accent-hover text-white rounded text-sm font-medium transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          View in Alerts
        </Link>
      </div>
    </div>
  );
}
