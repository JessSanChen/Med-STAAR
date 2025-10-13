import React, { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import AddProviderForm from '../partials/AddProviderForm';

function AddProvider() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      {/* Content */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-5xl mx-auto">
            <div className="mb-6">
              <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                Add Provider
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Register a new provider. No scheduling is done here.
              </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl p-6">
                <AddProviderForm />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default AddProvider;
