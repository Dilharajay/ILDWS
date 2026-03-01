import { create } from 'zustand';
import type { SensorNode, RiskZone, RiskLevel } from '../types';

interface MapState {
  nodes: Map<string, SensorNode>;
  riskZones: Map<string, RiskZone>;
  setNodes: (nodes: SensorNode[]) => void;
  setRiskZones: (zones: RiskZone[]) => void;
  updateNodeRisk: (nodeId: string, riskLevel: RiskLevel, riskScore: number) => void;
}

export const useMapStore = create<MapState>((set) => ({
  nodes: new Map(),
  riskZones: new Map(),

  setNodes: (nodes) =>
    set({
      nodes: new Map(nodes.map((n) => [n.node_id, n])),
    }),

  setRiskZones: (zones) =>
    set({
      riskZones: new Map(zones.map((z) => [z.slope_id, z])),
    }),

  updateNodeRisk: (nodeId, riskLevel, riskScore) =>
    set((state) => {
      const newNodes = new Map(state.nodes);
      const node = newNodes.get(nodeId);
      if (node) {
        newNodes.set(nodeId, { ...node, risk_level: riskLevel, risk_score: riskScore });
      }
      return { nodes: newNodes };
    }),
}));
