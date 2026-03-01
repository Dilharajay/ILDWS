import { create } from 'zustand';
import type { Alert } from '../types';

interface AlertState {
  activeAlerts: Alert[];
  alertHistory: Alert[];
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string) => void;
  clearAlert: (alertId: string) => void;
  setAlerts: (alerts: Alert[]) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  activeAlerts: [],
  alertHistory: [],

  addAlert: (alert) =>
    set((state) => ({
      activeAlerts: [alert, ...state.activeAlerts],
    })),

  acknowledgeAlert: (alertId) =>
    set((state) => ({
      activeAlerts: state.activeAlerts.map((a) =>
        a.alert_id === alertId ? { ...a, status: 'acknowledged' as const } : a
      ),
    })),

  clearAlert: (alertId) =>
    set((state) => ({
      activeAlerts: state.activeAlerts.filter((a) => a.alert_id !== alertId),
      alertHistory: [
        ...state.alertHistory,
        ...state.activeAlerts.filter((a) => a.alert_id === alertId),
      ],
    })),

  setAlerts: (alerts) =>
    set({
      activeAlerts: alerts.filter((a) => a.status === 'active'),
      alertHistory: alerts.filter((a) => a.status !== 'active'),
    }),
}));
