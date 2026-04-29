import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import {
  LayoutDashboard, Upload, Play, Table2
} from 'lucide-react';

import UploadPage    from '../components/UploadPage';
import SchedulerPage from '../components/SchedulerPage';
import PlanningPage  from '../components/PlanningPage';
import DashboardPage from '../components/DashboardPage';

const NAV = [
  { to: '/admin',           icon: LayoutDashboard, label: 'Tableau de bord' },
  { to: '/admin/upload',    icon: Upload,          label: 'Import données'  },
  { to: '/admin/scheduler', icon: Play,            label: 'Génération CSP'  },
  { to: '/admin/planning',  icon: Table2,          label: 'Planning'        },
];

export const DOMAIN_COLORS = {
  'Informatique': 'bg-blue-100 text-blue-800',
  'Electrique':   'bg-green-100 text-green-800',
  'Mecanique':    'bg-amber-100 text-amber-800',
  'Energetique':  'bg-red-100 text-red-800',
  'Genie Civil':  'bg-purple-100 text-purple-800',
};

export default function AdminPage() {
  return (
    <div className="min-h-screen">
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />

      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 bg-[var(--brand-navy)] text-white flex flex-col">
          <div className="px-6 py-6 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--brand-gold)] text-[var(--brand-navy)] font-bold">
                UIT
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-white/70">Administration</p>
                <p className="font-semibold text-white text-base">PFE Scheduler</p>
                <p className="text-xs text-white/60">Gestion des jurys</p>
              </div>
            </div>
          </div>

          <nav className="flex-1 px-4 py-5 space-y-2">
            {NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/admin'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all
                  ${isActive
                    ? 'bg-white/15 text-white shadow-sm'
                    : 'text-white/70 hover:bg-white/10 hover:text-white'}`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="px-4 pb-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.25em] text-white/60">Session 2026</p>
              <p className="mt-2 text-sm font-semibold text-white">Soutenances PFE</p>
              <p className="text-xs text-white/60">Suivi centralise des jurys</p>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/"          element={<DashboardPage />} />
            <Route path="/upload"    element={<UploadPage />} />
            <Route path="/scheduler" element={<SchedulerPage />} />
            <Route path="/planning"  element={<PlanningPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}