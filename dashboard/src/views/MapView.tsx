import { useState, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polygon,
  Popup,
  LayersControl,
} from 'react-leaflet';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { MapData, SensorNode, RiskLevel } from '../types';
import NodeDetailPanel from '../components/NodeDetailPanel';
import RedAlertModal from '../components/RedAlertModal';
import 'leaflet/dist/leaflet.css';

const RISK_COLORS: Record<RiskLevel, string> = {
  GREEN: '#22c55e',
  YELLOW: '#eab308',
  ORANGE: '#f97316',
  RED: '#ef4444',
};

function markerRadius(score: number): number {
  return Math.max(8, Math.round(8 + score * 10));
}

export default function MapView() {
  const [selectedNode, setSelectedNode] = useState<SensorNode | null>(null);
  const [redAlert, setRedAlert] = useState<{
    slopeName: string;
    riskScore: number;
    timestamp: string;
  } | null>(null);

  const { data: mapData } = useQuery<MapData>({
    queryKey: ['mapData'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/map/data');
      return res.data.data;
    },
    refetchInterval: 60_000,
  });

  const handleNodeClick = useCallback((node: SensorNode) => {
    setSelectedNode(node);
  }, []);

  const nodes = mapData?.nodes || [];
  const riskZones = mapData?.risk_zones || [];

  return (
    <div className="h-full flex relative">
      <div className="flex-1">
        <MapContainer
          center={[3.1, 101.7]}
          zoom={10}
          className="h-full w-full"
          style={{ background: '#0f172a' }}
        >
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="OpenStreetMap">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>

            <LayersControl.Overlay checked name="Node Markers">
              <>
                {nodes.map((node) => (
                  <CircleMarker
                    key={node.node_id}
                    center={[node.latitude, node.longitude]}
                    radius={markerRadius(node.risk_score)}
                    pathOptions={{
                      fillColor: RISK_COLORS[node.risk_level] || RISK_COLORS.GREEN,
                      fillOpacity: 0.8,
                      color: RISK_COLORS[node.risk_level] || RISK_COLORS.GREEN,
                      weight: 2,
                    }}
                    className={node.risk_level === 'RED' ? 'animate-pulse-red' : ''}
                    eventHandlers={{
                      click: () => handleNodeClick(node),
                    }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <strong>{node.node_id}</strong>
                        <br />
                        Risk: {node.risk_level} ({(node.risk_score * 100).toFixed(0)}%)
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
              </>
            </LayersControl.Overlay>

            <LayersControl.Overlay checked name="Risk Zones">
              <>
                {riskZones.map((zone) => (
                  <Polygon
                    key={zone.slope_id}
                    positions={zone.boundary}
                    pathOptions={{
                      fillColor: RISK_COLORS[zone.risk_level] || RISK_COLORS.GREEN,
                      fillOpacity: 0.3,
                      color: RISK_COLORS[zone.risk_level] || RISK_COLORS.GREEN,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <strong>{zone.slope_name}</strong>
                        <br />
                        Risk: {zone.risk_level} ({(zone.risk_score * 100).toFixed(0)}%)
                      </div>
                    </Popup>
                  </Polygon>
                ))}
              </>
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
      </div>

      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {redAlert && (
        <RedAlertModal
          slopeName={redAlert.slopeName}
          riskScore={redAlert.riskScore}
          timestamp={redAlert.timestamp}
          onAcknowledge={() => setRedAlert(null)}
        />
      )}
    </div>
  );
}
