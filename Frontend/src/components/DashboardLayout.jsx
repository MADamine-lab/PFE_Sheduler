import React from 'react';
import { Outlet } from 'react-router-dom';

const DashboardLayout = ({ children }) => {
  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen">
        {/* Sidebar simplifiee pour etudiants/professeurs */}
        <aside className="w-60 min-h-screen bg-[var(--brand-navy)] text-white">
          <div className="p-6 border-b border-white/10">
            <p className="text-xs uppercase tracking-[0.3em] text-white/60">Espace personnel</p>
            <h1 className="mt-2 text-lg font-semibold text-white">PFE Scheduler</h1>
            <p className="text-xs text-white/60">Suivi individuel</p>
          </div>
          <nav className="p-4">
            <div className="space-y-2">
              <a
                href="/"
                className="block rounded-xl px-4 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                Tableau de bord
              </a>
              <a
                href="/planning"
                className="block rounded-xl px-4 py-2 text-sm text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                Mon planning
              </a>
            </div>
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1">
          {children || <Outlet />}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;