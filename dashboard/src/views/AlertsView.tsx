import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import { Check, Eye, MapPin } from 'lucide-react';
import { apiClient } from '../api/client';
import type { Alert, RiskLevel } from '../types';

const LEVEL_COLORS: Record<RiskLevel, string> = {
  GREEN: 'bg-risk-green/20 text-risk-green border-risk-green',
  YELLOW: 'bg-risk-yellow/20 text-risk-yellow border-risk-yellow',
  ORANGE: 'bg-risk-orange/20 text-risk-orange border-risk-orange',
  RED: 'bg-risk-red/20 text-risk-red border-risk-red',
};

export default function AlertsView() {
  const [searchParams] = useSearchParams();
  const slopeFilter = searchParams.get('slope') || '';
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data: alertsResponse, isLoading } = useQuery({
    queryKey: ['alerts', page, levelFilter, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), limit: '20' });
      if (levelFilter) params.set('level', levelFilter);
      if (statusFilter) params.set('status', statusFilter);
      const res = await apiClient.get(`/v1/alerts?${params}`);
      return res.data;
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) =>
      apiClient.patch(`/v1/alerts/${alertId}/acknowledge`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });

  const resolveMutation = useMutation({
    mutationFn: (alertId: string) =>
      apiClient.patch(`/v1/alerts/${alertId}/resolve`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });

  const alerts: Alert[] = alertsResponse?.data || [];
  const meta = alertsResponse?.meta || {};

  const filteredAlerts = useMemo(() => {
    if (!slopeFilter) return alerts;
    return alerts.filter((a) => a.slope_id === slopeFilter);
  }, [alerts, slopeFilter]);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-text-primary">Alerts</h2>
        <div className="flex gap-3">
          <select
            value={levelFilter}
            onChange={(e) => { setLevelFilter(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-surface-dark border border-border rounded text-sm text-text-primary"
          >
            <option value="">All Levels</option>
            <option value="RED">RED</option>
            <option value="ORANGE">ORANGE</option>
            <option value="YELLOW">YELLOW</option>
            <option value="GREEN">GREEN</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-surface-dark border border-border rounded text-sm text-text-primary"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <p className="text-text-secondary">Loading alerts...</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-secondary text-left">
                  <th className="py-3 px-3">Alert ID</th>
                  <th className="py-3 px-3">Slope</th>
                  <th className="py-3 px-3">Level</th>
                  <th className="py-3 px-3">Score</th>
                  <th className="py-3 px-3">Triggered</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Acknowledged By</th>
                  <th className="py-3 px-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredAlerts.map((alert) => (
                  <tr key={alert.alert_id} className="hover:bg-surface-light/50">
                    <td className="py-3 px-3 font-mono text-xs text-text-primary">
                      {alert.alert_id}
                    </td>
                    <td className="py-3 px-3 text-text-primary">
                      {alert.slope_name || alert.slope_id}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                          LEVEL_COLORS[alert.risk_level] || ''
                        }`}
                      >
                        {alert.risk_level}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-text-primary font-mono">
                      {Math.round(alert.risk_score * 100)}%
                    </td>
                    <td className="py-3 px-3 text-text-secondary text-xs">
                      {new Date(alert.triggered_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`text-xs capitalize ${
                          alert.status === 'active'
                            ? 'text-risk-red'
                            : alert.status === 'acknowledged'
                            ? 'text-risk-yellow'
                            : 'text-risk-green'
                        }`}
                      >
                        {alert.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-text-secondary text-xs">
                      {alert.acknowledged_by || '—'}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex gap-2">
                        {alert.status === 'active' && (
                          <button
                            onClick={() => acknowledgeMutation.mutate(alert.alert_id)}
                            className="p-1 text-risk-yellow hover:text-risk-green"
                            title="Acknowledge"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                        {alert.status === 'acknowledged' && (
                          <button
                            onClick={() => resolveMutation.mutate(alert.alert_id)}
                            className="p-1 text-risk-green hover:text-text-primary"
                            title="Resolve"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                        <Link
                          to={`/?highlight=${alert.slope_id}`}
                          className="p-1 text-accent hover:text-accent-hover"
                          title="View on Map"
                        >
                          <MapPin className="w-4 h-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAlerts.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-text-secondary">
                      No alerts found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-text-secondary">
              Page {page} {meta.total ? `of ${Math.ceil(meta.total / 20)}` : ''}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 bg-surface-dark border border-border rounded text-sm text-text-primary disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={!meta.total || page * 20 >= meta.total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-surface-dark border border-border rounded text-sm text-text-primary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
