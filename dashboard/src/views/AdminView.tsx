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

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-text-primary mb-4">Administration</h2>
      <p className="text-text-secondary">Admin view — Coming in Prompt 7.4</p>
    </div>
  );
}
