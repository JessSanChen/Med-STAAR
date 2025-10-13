// src/partials/ProviderAvailabilitySheet.jsx
import React, { useEffect, useState } from 'react';

function parseCSV(text){const rows=[];let row=[],cell='',i=0,inQuotes=false;if(text.charCodeAt(0)===65279)text=text.slice(1);while(i<text.length){const ch=text[i];if(inQuotes){if(ch===`"`){if(text[i+1]===`"`) {cell+='"';i+=2;} else {inQuotes=false;i++;}} else {cell+=ch;i++;}} else {if(ch===`"`){inQuotes=true;i++;} else if(ch===`,`) {row.push(cell);cell='';i++;} else if(ch===`\r`) {if(text[i+1]===`\n`) i++; row.push(cell);rows.push(row);row=[];cell='';i++;} else if(ch===`\n`) {row.push(cell);rows.push(row);row=[];cell='';i++;} else {cell+=ch;i++;}}} if(cell.length||row.length){row.push(cell);rows.push(row);} return rows.filter(r=>r.length);}

export default function ProviderAvailabilitySheet() {
  const [headers, setHeaders] = useState([]), [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true), [err, setErr] = useState('');

  useEffect(() => {
    const url = `${window.location.origin}/provider_availability.csv`;
    (async () => {
      try {
        setLoading(true); setErr('');
        const res = await fetch(url, { cache: 'no-store' });
        const text = await res.text();
        const ctype = res.headers.get('content-type') || '';
        if (!res.ok || ctype.includes('text/html') || text.startsWith('<!DOCTYPE')) {
          throw new Error('CSV not found at /provider_availability.csv (got HTML). Put the file in /public.');
        }
        const all = parseCSV(text);
        if (!all.length) { setHeaders([]); setRows([]); }
        else { setHeaders(all[0]); setRows(all.slice(1)); }
      } catch (e) {
        setErr(String(e.message || e)); setHeaders([]); setRows([]);
      } finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      {loading && <div className="p-4 text-gray-500">Loading…</div>}
      {err && !loading && <div className="p-4 text-red-600">{err}</div>}
      {!loading && !err && (
        <div className="p-3">
          <div className="overflow-x-auto">
            <table className="table-auto w-[1200px] min-w-full">
              <thead className="text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50">
                <tr>{headers.map((h,i)=>(<th key={i} className="p-2 whitespace-nowrap align-top"><div className="font-semibold text-left">{h||'\u00A0'}</div></th>))}</tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-700/60">
                {rows.map((r,ri)=>(
                  <tr key={ri}>
                    {headers.map((_,ci)=>(
                      <td key={ci} className="p-2 whitespace-nowrap align-top">
                        <div className="text-left">{(r[ci]??'').trim()}</div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">Showing {rows.length} rows • {headers.length} columns</div>
        </div>
      )}
    </div>
  );
}
