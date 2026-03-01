import { useQuery } from '@tanstack/react-query';
import { Shield, Users, Activity, Database } from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuthStore } from '../store/authStore';

export default function AdminView() {
  const { user } = useAuthStore();

  if (user?.role !== 'admin') {
    return (
      <div className="p-6">
        <p className="text-risk-red">Access denied. Admin role required.</p>
      </div>
    );
  }

  const { data: healthResponse } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/system/health');
      return res.data;
    },
    refetchInterval: 30_000,
  });

  const { data: usersResponse } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/users');
      return res.data;
    },
  });

  const health = healthResponse?.data || {};
  const users = usersResponse?.data || [];

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-text-primary mb-6">Administration</h2>

      {/* System Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { icon: Activity, label: 'System Status', value: health.status || 'Unknown', color: 'text-risk-green' },
          { icon: Database, label: 'Database', value: health.database || 'Unknown', color: 'text-accent' },
          { icon: Users, label: 'Total Users', value: String(users.length), color: 'text-risk-yellow' },
          { icon: Shield, label: 'Your Role', value: user?.role || 'N/A', color: 'text-risk-orange' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="bg-primary border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <Icon className={`w-8 h-8 ${color}`} />
              <div>
                <p className="text-xs text-text-secondary">{label}</p>
                <p className="text-lg font-semibold text-text-primary capitalize">
                  {value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Users Table */}
      <h3 className="text-lg font-medium text-text-primary mb-4">Users</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-secondary text-left">
              <th className="py-3 px-3">Email</th>
              <th className="py-3 px-3">Name</th>
              <th className="py-3 px-3">Role</th>
              <th className="py-3 px-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {users.map((u: { id: string; email: string; full_name: string; role: string; is_active: boolean }) => (
              <tr key={u.id} className="hover:bg-surface-light/50">
                <td className="py-3 px-3 text-text-primary">{u.email}</td>
                <td className="py-3 px-3 text-text-primary">{u.full_name}</td>
                <td className="py-3 px-3 text-text-secondary capitalize">{u.role}</td>
                <td className="py-3 px-3">
                  <span className={u.is_active ? 'text-risk-green' : 'text-risk-red'}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
