import React, { useEffect, useMemo, useState } from 'react';
import LineChart from '../charts/LineChart02';

function PredictedVolumeGraph() {
  const [facilities, setFacilities] = useState([]);
  const [selected, setSelected] = useState('');
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Base API
  const API_BASE = useMemo(() => {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }, []);

  const toChartData = (payload) => {
    const pick = (label) => payload?.datasets?.find(d => d.label === label)?.data ?? [];
    return {
      labels: payload?.labels ?? [],
      datasets: [
        { label: 'md1', data: pick('md1'), borderColor: '#7c3aed', fill: false, borderWidth: 2, pointRadius: 0, tension: 0.2 },
        { label: 'md2', data: pick('md2'), borderColor: '#0ea5e9', fill: false, borderWidth: 2, pointRadius: 0, tension: 0.2 },
        { label: 'pm',  data: pick('pm'),  borderColor: '#22c55e', fill: false, borderWidth: 2, pointRadius: 0, tension: 0.2 },
      ],
    };
  };

  // Load forecast facilities
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setError('');
        const r = await fetch(`${API_BASE}/forecast/facilities`, { cache: 'no-store' });
        if (!r.ok) throw new Error();
        const data = await r.json();
        const list = Array.isArray(data.facilities) ? data.facilities : [];
        if (!list.length) throw new Error();
        if (alive) {
          setFacilities(list);
          setSelected((prev) => prev || list[0]);
        }
      } catch {
        if (alive) setError('Unable to load facilities.');
      }
    })();
    return () => { alive = false; };
  }, [API_BASE]);

  // Load forecast data for selected facility
  useEffect(() => {
    if (!selected) return;
    let alive = true;
    (async () => {
      try {
        setLoading(true);
        setError('');
        const r = await fetch(`${API_BASE}/forecast/${encodeURIComponent(selected)}`, { cache: 'no-store' });
        if (!r.ok) throw new Error();
        const payload = await r.json();
        if (alive) setChartData(toChartData(payload));
      } catch {
        if (alive) setError('Failed to load forecast data.');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [API_BASE, selected]);

  return (
    <div className="flex flex-col col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between gap-4">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">ETS with Weekly Seasonality</h2>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-300">Facility</label>
          <select
            className="text-sm border border-gray-200 dark:border-gray-700 rounded-md px-2 py-1 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {facilities.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      </header>

      {error && <div className="p-4 text-red-600">{error}</div>}
      {!error && loading && <div className="p-4 text-gray-500">Loading {selected}…</div>}
      {!error && !loading && chartData && (
        <LineChart data={chartData} width={995} height={320} title={selected} />
      )}
    </div>
  );
}

export default PredictedVolumeGraph;
