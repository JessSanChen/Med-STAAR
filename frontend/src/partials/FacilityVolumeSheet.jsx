// src/partials/FacilityVolumeSheet.jsx
import React, { useEffect, useState } from 'react';

function parseCSV(t) { const r = []; let o = [], e = '', i = 0, s = !1; if (t.charCodeAt(0) === 65279) t = t.slice(1); for (; i < t.length;) { const a = t[i]; if (s) if (a === `"`) { if (t[i + 1] === `"`) e += '"', i += 2; else s = !1, i += 1 } else e += a, i += 1; else a === `"` ? (s = !0, i += 1) : a === `,` ? (o.push(e), e = '', i += 1) : a === `\r` ? (t[i + 1] === `\n` && i++, o.push(e), r.push(o), o = [], e = '', i += 1) : a === `\n` ? (o.push(e), r.push(o), o = [], e = '', i += 1) : (e += a, i += 1) } return (e.length || o.length) && (o.push(e), r.push(o)), r.filter(n => n.length) }

export default function FacilityVolumeSheet() {
    const [headers, setHeaders] = useState([]), [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true), [err, setErr] = useState('');

    useEffect(() => {
        const url = `${window.location.origin}/facility_volume.csv`;
        (async () => {
            try {
                setLoading(true); setErr('');
                const res = await fetch(url, { cache: 'no-store' });
                const text = await res.text();
                const ctype = res.headers.get('content-type') || '';
                if (!res.ok || ctype.includes('text/html') || text.startsWith('<!DOCTYPE')) {
                    throw new Error('CSV not found at /facility_volume.csv (got HTML). Put the file in /public.');
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
                                <tr>{headers.map((h, i) => (<th key={i} className="p-2 whitespace-nowrap align-top"><div className="font-semibold text-left">{h || '\u00A0'}</div></th>))}</tr>
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
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">Showing {rows.length} rows • {headers.length} columns</div>
                </div>
            )}
        </div>
    );
}
