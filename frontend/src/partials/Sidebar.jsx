// src/partials/Sidebar.jsx
import React, { useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
// at the top with other imports
import SevaroLogo from '../images/sevaro-logo.png';


/** Icons copied from the original template, wrapped as tiny components */
const ICONS = {
  dashboard: (active) => (
    <svg width="16" height="16" viewBox="0 0 16 16"
      className={active ? "text-violet-600" : "text-gray-400"}>
      {/* Original "Dashboard" icon (two paths) */}
      <path fill="currentColor" d="M5.936.278A7.983 7.983 0 0 1 8 0a8 8 0 1 1-8 8c0-.722.104-1.413.278-2.064a1 1 0 1 1 1.932.516A5.99 5.99 0 0 0 2 8a6 6 0 1 0 6-6c-.53 0-1.045.076-1.548.21A1 1 0 1 1 5.936.278Z" />
      <path fill="currentColor" d="M6.068 7.482A2.003 2.003 0 0 0 8 10a2 2 0 1 0-.518-3.932L3.707 2.293a1 1 0 0 0-1.414 1.414l3.775 3.775Z" />
    </svg>
  ),
  file: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gray-400">
      {/* Original "file/doc" icon used throughout */}
      <path fill="currentColor" d="M2 2h9l3 3v9a2 2 0 0 1-2 2H2z" />
      <path fill="currentColor" d="M11 2v3h3" />
    </svg>
  ),
  calendar: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gray-400">
      {/* Original "Calendar" icon */}
      <path fill="currentColor" d="M5 4a1 1 0 0 0 0 2h6a1 1 0 1 0 0-2H5Z" />
      <path fill="currentColor" d="M4 0a4 4 0 0 0-4 4v8a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V4a4 4 0 0 0-4-4H4ZM2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Z" />
      <path fill="currentColor" d="M4 0a4 4 0 0 0-4 4v8a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V4a4 4 0 0 0-4-4H4ZM2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Z" />
    </svg>
  ),
  checks: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gray-400">
      {/* Original "Job Board" (double checks) icon */}
      <path fill="currentColor" d="M6.753 2.659a1 1 0 0 0-1.506-1.317L2.451 4.537l-.744-.744A1 1 0 1 0 .293 5.207l1.5 1.5a1 1 0 0 0 1.46-.048l3.5-4Z" />
      <path fill="currentColor" d="M6.753 10.659a1 1 0 1 0-1.506-1.317l-2.796 3.195-.744-.744a1 1 0 0 0-1.414 1.414l1.5 1.5a1 1 0 0 0 1.46-.049l3.5-4Z" />
      <path fill="currentColor" d="M8 4.5a1 1 0 0 1 1-1h6a1 1 0 1 1 0 2H9a1 1 0 0 1-1-1ZM9 11.5a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2H9Z" />
    </svg>
  ),
  megaphone: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gray-400">
      {/* Original "Campaigns" icon */}
      <path fill="currentColor" d="M6.649 1.018a1 1 0 0 1 .793 1.171L6.997 4.5h3.464l.517-2.689a1 1 0 1 1 1.964.378L12.498 4.5h2.422a1 1 0 0 1 0 2h-2.807l-.77 4h2.117a1 1 0 1 1 0 2h-2.501l-.517 2.689a1 1 0 1 1-1.964-.378l.444-2.311H5.46l-.517 2.689a1 1 0 1 1-1.964-.378l.444-2.311H1a1 1 0 1 1 0-2h2.807l.77-4H2.46a1 1 0 0 1 0-2h2.5l.518-2.689a1 1 0 0 1 1.17-.793ZM9.307 10.5l.77-4H6.612l-.77 4h3.464Z" />
    </svg>
  ),
  utility: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gray-400">
      {/* Original "Utility" icon */}
      <path fill="currentColor" d="M14.75 2.5a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5ZM14.75 16a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5ZM2.5 14.75a1.25 1.25 0 1 1-2.5 0 1.25 1.25 0 0 1 2.5 0ZM1.25 2.5a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5Z" />
      <path fill="currentColor" d="M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2ZM4 8a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z" />
    </svg>
  ),
};

function Sidebar({ sidebarOpen, setSidebarOpen }) {
  const { pathname } = useLocation();
  const trigger = useRef(null);
  const sidebar = useRef(null);

  // close on click outside (mobile)
  useEffect(() => {
    const clickHandler = (e) => {
      if (!sidebar.current || !trigger.current) return;
      if (!sidebarOpen) return;
      if (sidebar.current.contains(e.target) || trigger.current.contains(e.target)) return;
      setSidebarOpen(false);
    };
    document.addEventListener("click", clickHandler);
    return () => document.removeEventListener("click", clickHandler);
  }, [sidebarOpen, setSidebarOpen]);

  // close on ESC (mobile)
  useEffect(() => {
    const keyHandler = (e) => {
      if (!sidebarOpen) return;
      if (e.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", keyHandler);
    return () => document.removeEventListener("keydown", keyHandler);
  }, [sidebarOpen, setSidebarOpen]);

  const LinkItem = ({ to, label, icon }) => (
    <li>
      <NavLink
        end
        to={to}
        className={({ isActive }) =>
          `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
           ${isActive ? "text-violet-600 bg-violet-500/10" : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/60 dark:hover:bg-gray-700/50"}`
        }
        onClick={() => setSidebarOpen(false)}
      >
        <span className="shrink-0">{icon}</span>
        <span className="text-sm font-medium">{label}</span>
      </NavLink>
    </li>
  );

  return (
    <div className="min-w-fit">
      {/* Backdrop (mobile) */}
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden transition-opacity duration-200 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <div
        id="sidebar"
        ref={sidebar}
        className={`flex flex-col fixed z-50 left-0 top-0 h-[100dvh] w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700/60 p-4
                    transition-transform duration-200 lg:static lg:translate-x-0
                    ${sidebarOpen ? "translate-x-0" : "-translate-x-64"}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <NavLink to="/" className="flex items-center gap-2">
          <img src={SevaroLogo} alt="Sevaro" className="w-7 h-7" />
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Staffing Dashboard</span>
          </NavLink>

          {/* Close (mobile) */}
          <button
            ref={trigger}
            className="lg:hidden text-gray-500 hover:text-gray-400"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <svg className="w-6 h-6" viewBox="0 0 24 24">
              <path fill="currentColor" d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        {/* Simple tabs */}
        <nav className="flex-1">
          <ul className="space-y-1">
            <LinkItem
              to="/"
              label="Main"
              icon={ICONS.dashboard(pathname === "/")}
            />
{/* 
            <LinkItem
              to="/providers-tracker"
              label="Providers Tracker"
              icon={ICONS.utility()}
            /> */}

            <div className="mt-4 mb-1 text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 px-3">
              Actions
            </div>
            <LinkItem
              to="/add-providers"
              label="Add Providers"
              icon={ICONS.utility()}
            />
            {/* <LinkItem
              to="/submit-absences"
              label="Submit Sick Leaves"
              icon={ICONS.checks()}
            /> */}

            <div className="mt-4 mb-1 text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 px-3">
              System Data
            </div>
            <LinkItem
              to="/provider-availabilities"
              label="Provider Availabilities"
              icon={ICONS.file()}
            />
            <LinkItem
              to="/facility-coverage"
              label="Facility Coverage"
              icon={ICONS.file()}
            />
            <LinkItem
              to="/facility-volume"
              label="Facility Volume"
              icon={ICONS.file()}
            />
            <LinkItem
              to="/provider-credentialing"
              label="Provider Credentialing"
              icon={ICONS.file()}
            />

            <LinkItem
              to="/provider-contracts"
              label="Provider Contracts"
              icon={ICONS.file()}
            />

            <div className="mt-4 mb-1 text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 px-3">
              Models
            </div>
            <LinkItem
              to="/scheduler"
              label="Scheduler"
              icon={ICONS.calendar()}
            />
            <LinkItem
              to="/predicted-volume"
              label="Predicted Patient Volume"
              icon={ICONS.megaphone()}
            />
            <LinkItem
              to="/rescheduler"
              label="Rescheduler"
              icon={ICONS.utility()}
            />
            <LinkItem
              to="/fairness-report"
              label="Fairness Report"
              icon={ICONS.checks()}
            />
            
          </ul>
        </nav>
      </div>
    </div>
  );
}

export default Sidebar;
