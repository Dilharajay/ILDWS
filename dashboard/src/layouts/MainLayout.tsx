import { useState, useEffect } from 'react';
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom';
import {
  Map,
  Bell,
  Cpu,
  FileText,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Activity,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useWebSocket } from '../hooks/useWebSocket';

const navItems = [
  { path: '/', label: 'Map', icon: Map },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/nodes', label: 'Nodes', icon: Cpu },
  { path: '/reports', label: 'Reports', icon: FileText },
  { path: '/admin', label: 'Admin', icon: Settings },
];

export default function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user, isAuthenticated, logout } = useAuthStore();
  const { isConnected } = useWebSocket();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-surface-dark">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-56' : 'w-16'
        } bg-primary flex flex-col border-r border-border transition-all duration-200`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 p-4 border-b border-border">
          <Activity className="w-6 h-6 text-accent shrink-0" />
          {sidebarOpen && (
            <span className="text-lg font-bold text-text-primary">ILEWS</span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-2">
          {navItems.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path;
            if (path === '/admin' && user?.role !== 'admin') return null;
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                  active
                    ? 'bg-accent/20 text-accent border-r-2 border-accent'
                    : 'text-text-secondary hover:bg-surface-light hover:text-text-primary'
                }`}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {sidebarOpen && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex items-center justify-center p-3 border-t border-border text-text-secondary hover:text-text-primary"
        >
          {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </button>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top navigation bar */}
        <header className="h-14 bg-primary border-b border-border flex items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-medium text-text-secondary">
              Intelligent Landslide Early Warning System
            </h1>
          </div>
          <div className="flex items-center gap-4">
            {isConnected ? (
              <span className="flex items-center gap-1 text-xs text-risk-green">
                <Wifi className="w-3 h-3" /> Live
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-risk-orange">
                <WifiOff className="w-3 h-3" /> Reconnecting...
              </span>
            )}
            <span className="text-sm text-text-secondary">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={logout}
              className="flex items-center gap-1 text-sm text-text-secondary hover:text-risk-red transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
