// src/pages/FacilityCoverage.jsx
import React, { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import FacilityCoverageSheet from '../partials/FacilityCoverageSheet';

export default function FacilityCoverage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                Facility Coverage
              </h1>
            </div>
            <div className="grid grid-cols-12 gap-6">
              <FacilityCoverageSheet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
