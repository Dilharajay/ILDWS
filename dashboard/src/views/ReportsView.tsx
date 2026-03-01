import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, FileText } from 'lucide-react';
import { apiClient } from '../api/client';

interface Report {
  report_id: string;
  report_type: string;
  slope_id: string;
  slope_name?: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  file_url?: string;
}

export default function ReportsView() {
  const [typeFilter, setTypeFilter] = useState('');

  const { data: reportsResponse, isLoading } = useQuery({
    queryKey: ['reports', typeFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (typeFilter) params.set('type', typeFilter);
      const res = await apiClient.get(`/v1/reports?${params}`);
      return res.data;
    },
  });

  const reports: Report[] = reportsResponse?.data || [];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-text-primary">Reports</h2>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-1.5 bg-surface-dark border border-border rounded text-sm text-text-primary"
        >
          <option value="">All Types</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="incident">Incident</option>
        </select>
      </div>

      {isLoading ? (
        <p className="text-text-secondary">Loading reports...</p>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div
              key={report.report_id}
              className="bg-primary border border-border rounded-lg p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <FileText className="w-8 h-8 text-accent shrink-0" />
                <div>
                  <p className="text-text-primary font-medium">
                    {report.report_id}
                  </p>
                  <p className="text-sm text-text-secondary">
                    {report.slope_name || report.slope_id} · {report.report_type}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {new Date(report.period_start).toLocaleDateString()} —{' '}
                    {new Date(report.period_end).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-secondary">
                  {new Date(report.generated_at).toLocaleString()}
                </span>
                {report.file_url && (
                  <a
                    href={report.file_url}
                    className="p-2 text-accent hover:text-accent-hover"
                    title="Download"
                  >
                    <Download className="w-5 h-5" />
                  </a>
                )}
              </div>
            </div>
          ))}
          {reports.length === 0 && (
            <p className="text-center text-text-secondary py-8">
              No reports available
            </p>
          )}
        </div>
      )}
    </div>
  );
}
