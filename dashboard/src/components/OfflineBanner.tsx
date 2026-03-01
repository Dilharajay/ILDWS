import { WifiOff } from 'lucide-react';

export default function OfflineBanner() {
  return (
    <div className="bg-risk-orange/20 border-b border-risk-orange px-4 py-2 flex items-center gap-2 text-sm text-risk-orange">
      <WifiOff className="w-4 h-4" />
      <span>Connection lost — showing last known data</span>
    </div>
  );
}
