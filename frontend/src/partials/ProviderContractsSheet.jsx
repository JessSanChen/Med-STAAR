// src/partials/dashboard/ScheduleCard.jsx
import React, { useEffect, useState } from 'react';

// tiny CSV parser with quotes support
function parseCSV(text) {
  const rows = [];
  let row = [], cell = '';
  let i = 0, inQuotes = false;

  // strip UTF-8 BOM if present
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

  while (i < text.length) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 2; }
        else { inQuotes = false; i += 1; }
      } else { cell += ch; i += 1; }
    } else {
      if (ch === '"') { inQuotes = true; i += 1; }
      else if (ch === ',') { row.push(cell); cell = ''; i += 1; }
      else if (ch === '\r') {
        if (text[i + 1] === '\n') i += 1;
        row.push(cell); rows.push(row); row = []; cell = ''; i += 1;
      } else if (ch === '\n') {
        row.push(cell); rows.push(row); row = []; cell = ''; i += 1;
      } else { cell += ch; i += 1; }
    }
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.length);
}

function ProviderContractsSheet() {
  const [headers, setHeaders] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    // If the CSV is in /public, this resolves to https://host/final_schedule.csv
    const url = new URL('../../../public/provider_contract.csv', window.location.origin).toString();

    (async () => {
      try {
        setLoading(true); setErr('');
        const res = await fetch(url, { cache: 'no-store' });
        const text = await res.text();

        // Quick sanity checks: got HTML instead of CSV?
        const ctype = res.headers.get('content-type') || '';
        if (!res.ok || ctype.includes('text/html') || text.startsWith('<!DOCTYPE')) {
          throw new Error('CSV not found at /final_schedule.csv (got HTML). Make sure the file is in /public.');
        }

        const all = parseCSV(text);
        if (!all.length) { setHeaders([]); setRows([]); }
        else { setHeaders(all[0]); setRows(all.slice(1)); }
      } catch (e) {
        setErr(String(e.message || e));
        setHeaders([]); setRows([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl">


      {loading && <div className="p-4 text-gray-500">Loading schedule…</div>}
      {err && !loading && <div className="p-4 text-red-600">{err}</div>}

      {!loading && !err && (
        <div className="p-3">
          <div className="overflow-x-auto">
            <table className="table-auto w-[1200px] min-w-full">
              <thead className="text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  {headers.map((h, i) => (
                    <th key={i} className="p-2 whitespace-nowrap align-top">
                      <div className="font-semibold text-left">{h || '\u00A0'}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-700/60">
                {rows.map((r, ri) => (
                  <tr key={ri}>
                    {headers.map((_, ci) => (
                      <td key={ci} className="p-2 whitespace-nowrap align-top">
                        <div className="text-left">{(r[ci] ?? '').trim()}</div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Showing {rows.length} rows • {headers.length} columns
          </div>
        </div>
      )}
    </div>
  );
}

export default ProviderContractsSheet;
