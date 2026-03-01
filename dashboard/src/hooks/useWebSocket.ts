import { useEffect, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { useMapStore } from '../store/mapStore';
import { useAlertStore } from '../store/alertStore';
import type { RiskLevel, Alert } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/v1/ws';

const RISK_TOAST_COLORS: Record<RiskLevel, { bg: string; border: string }> = {
  GREEN: { bg: '#22c55e20', border: '#22c55e' },
  YELLOW: { bg: '#eab30820', border: '#eab308' },
  ORANGE: { bg: '#f9731620', border: '#f97316' },
  RED: { bg: '#ef444440', border: '#ef4444' },
};

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null);
  const reconnectDelayRef = useRef(2000);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval>>(null);
  const mountedRef = useRef(true);

  const token = useAuthStore((s) => s.token);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const updateNodeRisk = useMapStore((s) => s.updateNodeRisk);
  const addAlert = useAlertStore((s) => s.addAlert);

  const connect = useCallback(() => {
    if (!token || !mountedRef.current) return;

    try {
      const ws = new WebSocket(`${WS_URL}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectDelayRef.current = 2000;

        // Subscribe to all slopes
        ws.send(JSON.stringify({ type: 'subscribe', slopes: ['*'] }));

        // Start keepalive ping
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30_000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleMessage(msg);
        } catch {
          // Ignore unparseable messages
        }
      };

      ws.onclose = () => {
        cleanup();
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      scheduleReconnect();
    }
  }, [token]);

  const cleanup = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return;
    const delay = Math.min(reconnectDelayRef.current, 60_000);
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectDelayRef.current *= 2;
      connect();
    }, delay);
  }, [connect]);

  const handleMessage = useCallback(
    (msg: { type: string; data: Record<string, unknown> }) => {
      switch (msg.type) {
        case 'RISK_UPDATE': {
          const { node_id, risk_level, risk_score } = msg.data as {
            node_id: string;
            risk_level: RiskLevel;
            risk_score: number;
          };
          updateNodeRisk(node_id, risk_level, risk_score);
          break;
        }

        case 'ALERT_TRIGGERED': {
          const alert = msg.data as unknown as Alert;
          addAlert(alert);

          const level = alert.risk_level;
          const colors = RISK_TOAST_COLORS[level] || RISK_TOAST_COLORS.YELLOW;

          toast(
            `⚠ ${level} Alert: ${alert.slope_name || alert.slope_id} (${Math.round(alert.risk_score * 100)}%)`,
            {
              duration: level === 'RED' ? Infinity : 5000,
              style: {
                background: colors.bg,
                borderLeft: `4px solid ${colors.border}`,
                color: '#f1f5f9',
              },
            }
          );
          break;
        }

        case 'NODE_STATUS_CHANGE': {
          const { node_id, risk_level, risk_score } = msg.data as {
            node_id: string;
            risk_level: RiskLevel;
            risk_score: number;
          };
          if (risk_level && risk_score !== undefined) {
            updateNodeRisk(node_id, risk_level, risk_score);
          }
          break;
        }
      }
    },
    [updateNodeRisk, addAlert]
  );

  useEffect(() => {
    mountedRef.current = true;
    if (isAuthenticated && token) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      cleanup();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, token, connect, cleanup]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
