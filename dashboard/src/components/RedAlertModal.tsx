import { useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  slopeName: string;
  riskScore: number;
  timestamp: string;
  onAcknowledge: () => void;
}

function playAlertBeep() {
  try {
    const ctx = new AudioContext();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.frequency.value = 880;
    oscillator.type = 'square';
    gain.gain.value = 0.3;
    oscillator.start();

    // Beep pattern: on 200ms, off 200ms, repeat 3 times
    let count = 0;
    const interval = setInterval(() => {
      count++;
      if (count >= 6) {
        clearInterval(interval);
        oscillator.stop();
        ctx.close();
        return;
      }
      gain.gain.value = count % 2 === 0 ? 0.3 : 0;
    }, 200);

    return () => {
      clearInterval(interval);
      oscillator.stop();
      ctx.close();
    };
  } catch {
    // Web Audio API not available
  }
}

export default function RedAlertModal({
  slopeName,
  riskScore,
  timestamp,
  onAcknowledge,
}: Props) {
  const cleanupRef = useRef<(() => void) | undefined>(undefined);

  useEffect(() => {
    cleanupRef.current = playAlertBeep();
    return () => cleanupRef.current?.();
  }, []);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-risk-red/90 backdrop-blur-sm">
      <div className="bg-primary border-2 border-risk-red rounded-xl p-8 max-w-lg w-full mx-4 text-center shadow-2xl animate-pulse-red">
        <AlertTriangle className="w-16 h-16 text-risk-red mx-auto mb-4" />

        <h2 className="text-3xl font-bold text-risk-red mb-2">
          CRITICAL ALERT
        </h2>
        <h3 className="text-xl text-text-primary mb-6">{slopeName}</h3>

        <div className="bg-surface-dark rounded-lg p-4 mb-6 space-y-2">
          <div className="flex justify-between">
            <span className="text-text-secondary">Risk Score</span>
            <span className="text-risk-red font-bold text-lg">
              {Math.round(riskScore * 100)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Timestamp</span>
            <span className="text-text-primary">
              {new Date(timestamp).toLocaleString()}
            </span>
          </div>
        </div>

        <button
          onClick={onAcknowledge}
          className="w-full py-3 bg-risk-red hover:bg-red-600 text-white rounded-lg font-bold text-lg transition-colors"
        >
          ACKNOWLEDGE
        </button>
      </div>
    </div>
  );
}
