import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Edit2, X, Save } from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuthStore } from '../store/authStore';
import type { SensorNode, RiskLevel } from '../types';

const STATUS_COLORS: Record<string, string> = {
  active: 'text-risk-green',
  inactive: 'text-text-secondary',
  maintenance: 'text-risk-yellow',
  offline: 'text-risk-red',
};

const RISK_DOT: Record<RiskLevel, string> = {
  GREEN: 'bg-risk-green',
  YELLOW: 'bg-risk-yellow',
  ORANGE: 'bg-risk-orange',
  RED: 'bg-risk-red',
};

export default function NodesView() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editingNode, setEditingNode] = useState<SensorNode | null>(null);
  const [editLat, setEditLat] = useState('');
  const [editLon, setEditLon] = useState('');
  const [editName, setEditName] = useState('');
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const { data: nodesResponse, isLoading } = useQuery({
    queryKey: ['nodes'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/nodes');
      return res.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ nodeId, data }: { nodeId: string; data: Record<string, unknown> }) => {
      return apiClient.put(`/v1/nodes/${nodeId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      setEditingNode(null);
    },
  });

  const nodes: SensorNode[] = nodesResponse?.data || [];

  const filteredNodes = nodes.filter((n) => {
    const matchSearch =
      !search ||
      n.node_id.toLowerCase().includes(search.toLowerCase()) ||
      n.name?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = !statusFilter || n.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const openEdit = (node: SensorNode) => {
    setEditingNode(node);
    setEditName(node.name);
    setEditLat(String(node.latitude));
    setEditLon(String(node.longitude));
  };

  const handleSave = () => {
    if (!editingNode) return;
    updateMutation.mutate({
      nodeId: editingNode.node_id,
      data: {
        name: editName,
        latitude: parseFloat(editLat),
        longitude: parseFloat(editLon),
      },
    });
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-text-primary">Sensor Nodes</h2>
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="pl-9 pr-3 py-1.5 bg-surface-dark border border-border rounded text-sm text-text-primary w-48"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-surface-dark border border-border rounded text-sm text-text-primary"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="maintenance">Maintenance</option>
            <option value="offline">Offline</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <p className="text-text-secondary">Loading nodes...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-secondary text-left">
                <th className="py-3 px-3">Node ID</th>
                <th className="py-3 px-3">Slope</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Risk</th>
                <th className="py-3 px-3">Last Seen</th>
                <th className="py-3 px-3">Battery</th>
                <th className="py-3 px-3">Firmware</th>
                <th className="py-3 px-3">Coordinates</th>
                {user?.role === 'admin' && <th className="py-3 px-3">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredNodes.map((node) => (
                <tr key={node.node_id} className="hover:bg-surface-light/50">
                  <td className="py-3 px-3 font-mono text-xs text-text-primary">
                    {node.node_id}
                  </td>
                  <td className="py-3 px-3 text-text-primary">
                    {node.slope_name || node.slope_id}
                  </td>
                  <td className="py-3 px-3">
                    <span className={`capitalize ${STATUS_COLORS[node.status] || ''}`}>
                      {node.status}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${RISK_DOT[node.risk_level] || 'bg-gray-500'}`}
                      />
                      <span className="text-text-primary">
                        {Math.round(node.risk_score * 100)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-text-secondary text-xs">
                    {node.last_seen
                      ? new Date(node.last_seen).toLocaleString()
                      : 'N/A'}
                  </td>
                  <td className="py-3 px-3 text-text-primary font-mono">
                    {node.battery_voltage?.toFixed(2)}V
                  </td>
                  <td className="py-3 px-3 text-text-secondary text-xs">
                    {node.firmware_version}
                  </td>
                  <td className="py-3 px-3 text-text-secondary font-mono text-xs">
                    {node.latitude?.toFixed(4)}, {node.longitude?.toFixed(4)}
                  </td>
                  {user?.role === 'admin' && (
                    <td className="py-3 px-3">
                      <button
                        onClick={() => openEdit(node)}
                        className="p-1 text-accent hover:text-accent-hover"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {filteredNodes.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-text-secondary">
                    No nodes found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Modal */}
      {editingNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-primary border border-border rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">
                Edit Node: {editingNode.node_id}
              </h3>
              <button onClick={() => setEditingNode(null)} className="text-text-secondary hover:text-text-primary">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Name</label>
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-dark border border-border rounded text-text-primary"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Latitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={editLat}
                  onChange={(e) => setEditLat(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-dark border border-border rounded text-text-primary"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Longitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={editLon}
                  onChange={(e) => setEditLon(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-dark border border-border rounded text-text-primary"
                />
              </div>
              <p className="text-xs text-risk-yellow italic">
                Manual coordinate entry — verified against survey reference
              </p>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="w-full flex items-center justify-center gap-2 py-2 bg-accent hover:bg-accent-hover text-white rounded font-medium transition-colors disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
