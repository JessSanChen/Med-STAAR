import React, { useEffect, useMemo, useState } from "react";
import Sidebar from "../partials/Sidebar";
import Header from "../partials/Header";

// tiny CSV parser (supports quotes)
function parseCSV(text) {
  const rows = [];
  let row = [], cell = "";
  let i = 0, inQuotes = false;

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
      else if (ch === ",") { row.push(cell); cell = ""; i += 1; }
      else if (ch === "\r") {
        if (text[i + 1] === "\n") i += 1;
        row.push(cell); rows.push(row); row = []; cell = ""; i += 1;
      } else if (ch === "\n") {
        row.push(cell); rows.push(row); row = []; cell = ""; i += 1;
      } else { cell += ch; i += 1; }
    }
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.length);
}

export default function Rescheduler() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [headers, setHeaders] = useState([]);
  const [records, setRecords] = useState([]); // raw rows as objects
  const [loadingCSV, setLoadingCSV] = useState(true);
  const [errorCSV, setErrorCSV] = useState("");

  const [shift, setShift] = useState("");
  const [date, setDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState([]);

  // Load CSV from /public
  useEffect(() => {
    (async () => {
      try {
        setLoadingCSV(true); setErrorCSV("");
        const res = await fetch("/replacement_analysis.csv", { cache: "no-store" });
        const text = await res.text();

        if (!res.ok || text.startsWith("<!DOCTYPE")) {
          throw new Error("Could not load replacement_analysis.csv from /public");
        }

        const rows = parseCSV(text);
        if (!rows.length) throw new Error("CSV is empty");

        const head = rows[0];
        const body = rows.slice(1);
        setHeaders(head);

        const idx = Object.fromEntries(head.map((h, i) => [h, i]));

        // Map to objects, drop empty lines
        const objs = body
          .filter(r => r.some(v => v && v.trim().length))
          .map(r => ({
            provider_name: r[idx["provider_name"]] || "",
            viability_score: r[idx["viability_score"]] || "",
            date: r[idx["date"]] || "",
            shift_type: r[idx["shift_type"]] || "",
            // keep raw row if ever needed later
          }));

        setRecords(objs);
      } catch (e) {
        setErrorCSV(String(e.message || e));
      } finally {
        setLoadingCSV(false);
      }
    })();
  }, []);

  // Distill selectable options from CSV
  const shiftOptions = useMemo(() => {
    const set = new Set(records.map(r => r.shift_type).filter(Boolean));
    return Array.from(set).sort();
  }, [records]);

  const dateOptions = useMemo(() => {
    const set = new Set(records.map(r => r.date).filter(Boolean));
    return Array.from(set).sort();
  }, [records]);

  // Submit handler
  const onSubmit = (e) => {
    e.preventDefault();
    setResults([]);
    setSubmitting(true);

    // simulate a brief “thinking” pause
    setTimeout(() => {
      // Filter to selected shift/date and keep only provider_name + viability_score
      const filtered = records
        .filter(r => (!shift || r.shift_type === shift) && (!date || r.date === date))
        .filter(r => r.provider_name && r.viability_score && !Number.isNaN(Number(r.viability_score)))
        .map(r => ({
          provider_name: r.provider_name,
          viability_score: Number(r.viability_score)
        }))
        .sort((a, b) => b.viability_score - a.viability_score);

      setResults(filtered);
      setSubmitting(false);
    }, 1400);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-5xl mx-auto">
            <div className="bg-white border border-gray-200 rounded-xl shadow-xs p-6">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-6">Rescheduler</h1>

              {/* Form */}
              <form onSubmit={onSubmit} className="grid sm:grid-cols-3 gap-4 items-end mb-6">
                {/* Shift */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Shift</label>
                  <select
                    className="w-full border border-gray-300 rounded-md px-3 py-2 bg-white text-gray-900"
                    value={shift}
                    onChange={(e) => setShift(e.target.value)}
                  >
                    <option value="">All</option>
                    {shiftOptions.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </div>

                {/* Date */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <select
                    className="w-full border border-gray-300 rounded-md px-3 py-2 bg-white text-gray-900"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  >
                    <option value="">All</option>
                    {dateOptions.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </div>

                {/* Button */}
                <div className="flex">
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-60"
                    disabled={loadingCSV || submitting}
                  >
                    {submitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"></path>
                        </svg>
                        Rescheduling…
                      </>
                    ) : (
                      "Reschedule"
                    )}
                  </button>
                </div>
              </form>

              {/* Messages */}
              {loadingCSV && <div className="text-gray-600">Loading candidates…</div>}
              {errorCSV && !loadingCSV && (
                <div className="text-red-600">Error: {errorCSV}</div>
              )}

              {/* Results */}
              {!loadingCSV && !errorCSV && (
                <>
                  {results.length > 0 ? (
                    <>
                      <div className="text-sm text-gray-600 mb-3">
                        Showing {results.length} candidates
                        {shift && <> for <span className="font-semibold">{shift}</span></>}
                        {date && <> on <span className="font-semibold">{date}</span></>}
                      </div>
                      <div className="overflow-x-auto">
                        <table className="table-auto w-full min-w-[520px]">
                          <thead className="text-xs font-semibold uppercase text-gray-500 bg-gray-50">
                            <tr>
                              <th className="p-2 text-left">Rank</th>
                              <th className="p-2 text-left">Provider</th>
                              <th className="p-2 text-left">Viability Score</th>
                            </tr>
                          </thead>
                          <tbody className="text-sm divide-y divide-gray-100">
                            {results.map((r, i) => (
                              <tr key={`${r.provider_name}-${i}`}>
                                <td className="p-2 text-gray-900">{i + 1}</td>
                                <td className="p-2 text-gray-900">{r.provider_name}</td>
                                <td className="p-2 text-gray-900">{r.viability_score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <div className="text-gray-600">
                      {submitting ? "Rescheduling…" : "Pick options and press Reschedule to see candidates."}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
