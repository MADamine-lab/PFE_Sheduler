import React, { useEffect, useState } from 'react';
import { getDashboard, getAdminData } from '../auth/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import {
  Users, BookOpen, CalendarCheck, Server, TrendingUp, AlertCircle, FileSpreadsheet
} from 'lucide-react';

const COLORS = ['#1D4ED8','#0F766E','#B45309','#BE123C','#7C3AED'];

function StatCard({ icon: Icon, label, value, sub, color = 'blue' }) {
  const colorMap = {
    blue:   'bg-blue-50 text-blue-700',
    green:  'bg-green-50 text-green-700',
    amber:  'bg-amber-50 text-amber-700',
    purple: 'bg-purple-50 text-purple-700',
  };
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={`p-2.5 rounded-lg ${colorMap[color]}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [adminData, setAdminData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getDashboard(), getAdminData()])
      .then(([dashboardRes, adminRes]) => {
        setData(dashboardRes.data);
        setAdminData(adminRes.data);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="page-shell flex items-center gap-3 text-gray-500">
      <div className="spinner" /> Chargement du tableau de bord…
    </div>
  );

  if (error) return (
    <div className="page-shell">
      <div className="card p-6 border-amber-200 bg-amber-50">
        <div className="flex items-center gap-2 text-amber-700">
          <AlertCircle size={18} />
          <p className="font-medium">Aucune donnee disponible</p>
        </div>
        <p className="text-sm text-amber-600 mt-1">
          Importez d'abord un fichier Excel, puis lancez la generation CSP.
        </p>
      </div>
    </div>
  );

  const { counts, by_domain, jury_load, by_date, avg_nlp_scores } = data;
  const students = adminData?.etudiants || [];
  const taux = counts.etudiants > 0
    ? Math.round((counts.affectations / counts.etudiants) * 100)
    : 0;

  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Tableau de bord</p>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-white">Planification des soutenances PFE</h1>
            <p className="mt-2 text-sm text-white/75">
              Vue d'ensemble, statistiques et pilotage des jurys.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-white/80">
            <span className="rounded-full border border-white/30 bg-white/10 px-3 py-1">
              Session 2026
            </span>
            <span className="rounded-full border border-white/30 bg-white/10 px-3 py-1">
              {counts.etudiants} etudiants
            </span>
            <span className="rounded-full border border-white/30 bg-white/10 px-3 py-1">
              {counts.professeurs} professeurs
            </span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={Users}        label="Étudiants"      value={counts.etudiants}    color="blue" />
        <StatCard icon={BookOpen}     label="Professeurs"    value={counts.professeurs}  color="green" />
        <StatCard icon={CalendarCheck}label="Affectations"   value={counts.affectations}
                  sub={`${taux}% de réussite`} color="amber" />
        <StatCard icon={Server}       label="Créneaux dispo" value={counts.creneaux}     color="purple" />
      </div>

      {/* NLP Score banner */}
      {counts.affectations > 0 && (
        <div className="card p-4 flex items-center gap-6 border-blue-100 bg-blue-50">
          <TrendingUp size={20} className="text-blue-700 flex-shrink-0" />
          <div className="flex gap-8 text-sm">
            <div>
              <span className="text-blue-500">Score NLP moyen Examinateur : </span>
              <span className="font-bold text-blue-800">
                {(avg_nlp_scores.examinateur * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-blue-500">Score NLP moyen Président : </span>
              <span className="font-bold text-blue-800">
                {(avg_nlp_scores.president * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Répartition par domaine - Pie */}
        <div className="card p-5">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Répartition par domaine</h2>
          {by_domain.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={by_domain} dataKey="count" nameKey="domaine"
                     cx="50%" cy="50%" outerRadius={90} label={({ domaine, percent }) =>
                       `${domaine} (${(percent * 100).toFixed(0)}%)`
                     } labelLine={false}>
                  {by_domain.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v} étudiants`]} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-400 text-center py-10">Aucune donnée</p>}
        </div>

        {/* Charge des jurys - Bar */}
        <div className="card p-5">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Top 10 — Charge des jurys
          </h2>
          {jury_load.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={jury_load.slice(0, 10)} layout="vertical"
                        margin={{ left: 60, right: 20, top: 0, bottom: 0 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="prof" width={60}
                       tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" name="Soutenances" fill="#1D4ED8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-400 text-center py-10">Aucune affectation</p>}
        </div>

        {/* Planning par date */}
        <div className="card p-5 xl:col-span-2">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Soutenances par journée
          </h2>
          {by_date.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={by_date} margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Soutenances" fill="#0F766E" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-400 text-center py-10">Aucun planning généré</p>}
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Étudiants, sujets et encadrants</h2>
            <p className="text-sm text-gray-500 mt-1">
              Consultation des dossiers étudiants importés. L'import accepte les fichiers Excel et CSV.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-blue-700 bg-blue-50 px-3 py-2 rounded-lg">
            <FileSpreadsheet size={16} />
            {students.length} étudiants
          </div>
        </div>

        {students.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="py-3 pr-4 font-medium">Nom</th>
                  <th className="py-3 pr-4 font-medium">Domaine</th>
                  <th className="py-3 pr-4 font-medium">Sujet</th>
                  <th className="py-3 pr-4 font-medium">Encadrant</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {students.map((student) => (
                  <tr key={student.id} className="align-top">
                    <td className="py-4 pr-4 font-medium text-gray-900">
                      {student.prenom} {student.nom}
                    </td>
                    <td className="py-4 pr-4 text-gray-700">{student.domaine}</td>
                    <td className="py-4 pr-4 text-gray-700 max-w-lg">
                      <div className="line-clamp-2 whitespace-pre-wrap">
                        {student.sujet || 'Aucun sujet renseigné'}
                      </div>
                    </td>
                    <td className="py-4 pr-4 text-gray-700">
                      {student.encadrant_nom || 'Aucun encadrant'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-10">Aucun étudiant trouvé</p>
        )}
      </div>
    </div>
  );
}
