import { createBrowserRouter, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import MapView from './views/MapView';
import AlertsView from './views/AlertsView';
import NodesView from './views/NodesView';
import ReportsView from './views/ReportsView';
import AdminView from './views/AdminView';
import LoginView from './views/LoginView';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginView />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <MapView /> },
      { path: 'alerts', element: <AlertsView /> },
      { path: 'nodes', element: <NodesView /> },
      { path: 'reports', element: <ReportsView /> },
      { path: 'admin', element: <AdminView /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
