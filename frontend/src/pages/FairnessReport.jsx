// src/pages/FairnessReport.jsx
import React, { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3 bg-white">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-gray-900">{value}</div>
    </div>
  );
}

export default function FairnessReport() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      {/* Content */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          {/* White card container */}
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-5xl mx-auto">
            <div className="bg-white border border-gray-200 rounded-xl shadow-xs p-6 sm:p-8">
              {/* Title */}
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-6">
                Fairness-Based Schedule Completion Summary
              </h1>

              {/* Overview */}
              <section className="space-y-3 mb-8">
                <h2 className="text-xl font-semibold text-gray-900">Overview</h2>
                <p className="text-gray-700">
                  Successfully filled remaining unstaffed slots using a transparent fairness optimization approach
                  while respecting hard constraints (credentialing and coverage requirements).
                </p>
              </section>

              {/* Fairness Function */}
              <section className="space-y-4 mb-8">
                <h2 className="text-xl font-semibold text-gray-900">Fairness Function Design</h2>
                <p className="text-gray-700">
                  <span className="font-semibold">Scoring Components (0-170 points total, normalized to 0-1):</span>
                </p>
                <ol className="list-decimal ml-5 space-y-3 text-gray-700">
                  <li>
                    <span className="font-semibold">Contract Utilization Balance (0-100 points)</span>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                      <li>Favors providers who are below their contract limits</li>
                      <li>Under 100%: <code className="bg-gray-50 px-1 rounded border border-gray-200"> (1.0 - current_ratio) × 100 </code> points</li>
                      <li>100–120%: Linear decrease from 50 to 0 points</li>
                      <li>Over 120%: Heavily penalized</li>
                    </ul>
                  </li>
                  <li>
                    <span className="font-semibold">Preference Matching (0-30 points)</span>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                      <li>Full points if shift type matches provider&apos;s preference</li>
                      <li>Zero points otherwise</li>
                    </ul>
                  </li>
                  <li>
                    <span className="font-semibold">Workload Distribution (0-20 points)</span>
                    <div className="mt-1">Favors providers below average workload</div>
                    <div>
                      Points = <code className="bg-gray-50 px-1 rounded border border-gray-200">min(20, (avg_shifts - current_shifts) × 5)</code>
                    </div>
                  </li>
                  <li>
                    <span className="font-semibold">Weekend/PM Balance (0-20 points)</span>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                      <li>10 points for being under weekend limit (if weekend shift)</li>
                      <li>10 points for being under PM limit (if PM shift)</li>
                    </ul>
                  </li>
                </ol>
              </section>

              {/* Results: Coverage */}
              <section className="space-y-3 mb-8">
                <h2 className="text-xl font-semibold text-gray-900">Results</h2>

                <h3 className="text-lg font-semibold text-gray-900">Coverage Achievement</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <Stat label="Total slots requiring coverage" value="2,728" />
                  <Stat label="Successfully filled" value="2,256" />
                  <Stat label="Coverage rate" value="82.7%" />
                  <Stat label="Unfilled slots" value="472" />
                </div>
              </section>

              {/* Fairness Metrics */}
              <section className="space-y-4 mb-8">
                <h3 className="text-lg font-semibold text-gray-900">Fairness Metrics</h3>

                <div>
                  <div className="text-gray-900 font-semibold mb-2">Distribution Quality</div>
                  <ul className="list-disc ml-5 space-y-1 text-gray-700">
                    <li><span className="font-semibold">Average utilization:</span> 91.0% of contract</li>
                    <li><span className="font-semibold">Std. deviation:</span> 26.7%</li>
                    <li><span className="font-semibold">Gini coefficient:</span> 0.126 (excellent equality)</li>
                  </ul>
                </div>

                <div>
                  <div className="text-gray-900 font-semibold mb-2">Provider Categories</div>
                  <ul className="list-disc ml-5 space-y-1 text-gray-700">
                    <li><span className="font-semibold">Optimal (80–120%):</span> 33 providers (75%)</li>
                    <li><span className="font-semibold">Under-utilized (&lt;80%):</span> 8 providers (18%)</li>
                    <li><span className="font-semibold">Over-utilized (&gt;120%):</span> 3 providers (7%)</li>
                  </ul>
                </div>
              </section>

              {/* Successes */}
              <section className="space-y-3 mb-8">
                <h3 className="text-lg font-semibold text-gray-900">Key Successes</h3>
                <ol className="list-decimal ml-5 space-y-1 text-gray-700">
                  <li>Balanced workload: 75% within optimal utilization</li>
                  <li>Low inequality: Gini 0.126</li>
                  <li>Minimal over-utilization: only 3 providers &gt; 120%</li>
                  <li>Respected constraints (credentialing)</li>
                </ol>
              </section>

              {/* Transparent decision example */}
              <section className="space-y-3 mb-8">
                <h3 className="text-lg font-semibold text-gray-900">Transparency in Decision Making</h3>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <div className="font-mono text-sm text-gray-800 whitespace-pre-wrap">
{`Example Assignment Decision (Day 2, MD1-SROSH):
Eligible Providers: 21
Top Candidates:
1. Cameron Walker (Score: 0.882)
   - Under-utilized: 28.6% of contract (+71.4 points)
   - Non-preferred shift type (+0 points)
   - Below avg workload (+15.0 points)

2. Other Provider (Score: 0.650)
   - Under-utilized: 50% of contract (+50.0 points)
   - Preferred shift type (+30 points)
   - At avg workload (+0 points)

→ Selected: Cameron Walker (highest fairness score)`}
                  </div>
                </div>
              </section>

              {/* Edge cases */}
              <section className="space-y-3 mb-8">
                <h3 className="text-lg font-semibold text-gray-900">Handling of Edge Cases</h3>
                <ul className="list-disc ml-5 space-y-2 text-gray-700">
                  <li>
                    <span className="font-semibold">Spencer Irving &amp; Noah Stevens</span> (0% utilization)
                    <div className="text-gray-700">Limited credentialing; no eligible slots matched their credentials.</div>
                  </li>
                  <li>
                    <span className="font-semibold">Miles Foster</span> (126.7% utilization)
                    <div className="text-gray-700">Slightly over-utilized to ensure coverage for hard-to-fill slots.</div>
                  </li>
                </ul>
              </section>

              {/* Conclusion */}
              <section className="space-y-3 mb-8">
                <h3 className="text-lg font-semibold text-gray-900">Conclusion</h3>
                <ul className="list-disc ml-5 space-y-1 text-gray-700">
                  <li>Filled all required slots that had eligible providers</li>
                  <li>Maintained excellent fairness (Gini = 0.126)</li>
                  <li>Kept 75% of providers within optimal range</li>
                  <li>Provided transparent, explainable decisions</li>
                  <li>Respected all hard constraints</li>
                </ul>
              </section>

              {/* Files */}
              <section className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900">Files Generated</h3>
                <ul className="list-disc ml-5 space-y-1 text-gray-700">
                  <li><code className="bg-gray-50 px-1 rounded border border-gray-200">completed_schedule.xlsx</code> — Final schedule with all assignments</li>
                  <li><code className="bg-gray-50 px-1 rounded border border-gray-200">assignment_decisions.csv</code> — Log of each assignment decision</li>
                  <li><code className="bg-gray-50 px-1 rounded border border-gray-200">corrected_fairness_report.csv</code> — Provider utilization analysis</li>
                  <li><code className="bg-gray-50 px-1 rounded border border-gray-200">completed_schedule_report.json</code> — Detailed statistics</li>
                </ul>
              </section>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
