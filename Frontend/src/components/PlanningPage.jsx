import React, { useState, useEffect, useCallback } from 'react';
import {
  getAffectations, getProfesseurs, getCreneaux,
  updateAffectation, exportExcel, exportPDF
} from '../auth/api';
import toast from 'react-hot-toast';
import { Search, Filter, Edit2, Check, X, ChevronLeft, ChevronRight, FileSpreadsheet, FileText } from 'lucide-react';
import { DOMAIN_COLORS } from '../App';

const DOMAINES = ['', 'Informatique', 'Electrique', 'Mecanique', 'Energetique', 'Genie Civil'];

function ScoreBadge({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 60 ? 'bg-green-100 text-green-800'
              : pct >= 30 ? 'bg-amber-100 text-amber-800'
              :             'bg-red-100 text-red-700';
  return <span className={`badge ${color}`}>{pct}%</span>;
}

function EditRow({ aff, profs, creneaux, onSave, onCancel }) {
  const [examId, setExamId] = useState(aff.examinateur?.id || '');
  const [presId, setPresId] = useState(aff.president?.id || '');
  const [crId,   setCrId]   = useState(aff.creneau?.id || '');
  const [saving, setSaving] = useState(false);
  
  const handleSave = async () => {
    setSaving(true);
    try {
      await updateAffectation(aff.id, {
        examinateur_id: examId,
        president_id: presId,
        creneau_id: crId,
      });
      toast.success('Affectation mise à jour');
      onSave();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const encId = aff.encadrant?.id;
  const eligibleProfs = profs.filter(p => p.id !== encId);

  return (
    <tr className="bg-blue-50">
      <td className="table-td font-mono text-xs">{aff.etudiant?.id}</td>
      <td className="table-td">
        <div className="font-medium text-gray-900">{aff.etudiant?.prenom} {aff.etudiant?.nom}</div>
        <div className="text-xs text-gray-400 truncate max-w-xs">{aff.etudiant?.sujet?.slice(0, 50)}…</div>
      </td>
      <td className="table-td text-xs text-gray-500">{aff.encadrant?.prenom} {aff.encadrant?.nom}</td>
      <td className="table-td">
        <select className="select text-xs" value={examId} onChange={e => setExamId(e.target.value)}>
          {eligibleProfs.map(p => (
            <option key={p.id} value={p.id}>{p.prenom} {p.nom}</option>
          ))}
        </select>
      </td>
      <td className="table-td">
        <select className="select text-xs" value={presId} onChange={e => setPresId(e.target.value)}>
          {eligibleProfs.map(p => (
            <option key={p.id} value={p.id}>{p.prenom} {p.nom}</option>
          ))}
        </select>
      </td>
      <td className="table-td">
        <select className="select text-xs" value={crId} onChange={e => setCrId(e.target.value)}>
          {creneaux.map(c => (
            <option key={c.id} value={c.id}>{c.date} {c.slot} — {c.salle}</option>
          ))}
        </select>
      </td>
      <td className="table-td text-center">—</td>
      <td className="table-td">
        <div className="flex gap-1">
          <button onClick={handleSave} disabled={saving}
                  className="p-1.5 rounded-lg bg-green-100 hover:bg-green-200 text-green-700">
            {saving ? <div className="spinner w-3 h-3" /> : <Check size={14} />}
          </button>
          <button onClick={onCancel}
                  className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600">
            <X size={14} />
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function PlanningPage() {
  const [data, setData]         = useState([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [pages, setPages]       = useState(1);
  const [loading, setLoading]   = useState(false);
  const [editId, setEditId]     = useState(null);
  const [profs, setProfs]       = useState([]);
  const [creneaux, setCreneaux] = useState([]);
  const [filters, setFilters]   = useState({ domaine: '', date: '' });
  const [search, setSearch]     = useState('');
  const [exporting, setExporting] = useState('');

  const perPage = 15;

  const load = useCallback(async (p = page) => {
  setLoading(true);
  try {
    const res = await getAffectations({
      page: p, per_page: perPage,
      domaine: filters.domaine,
      date: filters.date,
    });

    // ✅ DRF PageNumberPagination returns: { count, next, previous, results }
    const responseData = res.data;
    setData(responseData.results || []);           // ← was res.data.data
    setTotal(responseData.count || 0);             // ← was res.data.total
    setPages(Math.ceil((responseData.count || 0) / perPage)); // ← was res.data.pages

  } catch (e) {
    toast.error('Erreur de chargement');
    setData([]);   // ✅ prevent undefined crash
  } finally {
    setLoading(false);
  }
  }, [page, filters]);

  useEffect(() => { load(1); setPage(1); }, [filters]);
  useEffect(() => { load(page); }, [page]);

  useEffect(() => {
    getProfesseurs().then(r => setProfs(r.data)).catch(() => {});
    getCreneaux().then(r => setCreneaux(r.data)).catch(() => {});
  }, []);

  const displayed = search
    ? data.filter(a =>
        `${a.etudiant?.nom} ${a.etudiant?.prenom} ${a.etudiant?.sujet}`
          .toLowerCase().includes(search.toLowerCase())
      )
    : data;

  const handleExport = async (type) => {
    setExporting(type);
    try {
      if (type === 'excel') await exportExcel();
      else await exportPDF();
      toast.success('Export téléchargé');
    } catch { toast.error('Erreur export'); }
    finally { setExporting(''); }
  };

  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-white/70">Planning</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Planning des soutenances</h1>
            <p className="mt-2 text-sm text-white/75">{total} affectations generees</p>
          </div>
          <div className="flex gap-2">
          <button className="btn-secondary flex items-center gap-2 text-sm"
                  onClick={() => handleExport('excel')} disabled={exporting === 'excel'}>
            <FileSpreadsheet size={16} className="text-green-600" />
            {exporting === 'excel' ? 'Export…' : 'Excel'}
          </button>
          <button className="btn-secondary flex items-center gap-2 text-sm"
                  onClick={() => handleExport('pdf')} disabled={exporting === 'pdf'}>
            <FileText size={16} className="text-red-600" />
            {exporting === 'pdf' ? 'Export…' : 'PDF'}
          </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-3 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input className="input pl-8 text-sm" placeholder="Rechercher étudiant, sujet…"
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          <select className="select text-sm w-44"
                  value={filters.domaine}
                  onChange={e => setFilters(f => ({ ...f, domaine: e.target.value }))}>
            {DOMAINES.map(d => (
              <option key={d} value={d}>{d || 'Tous les domaines'}</option>
            ))}
          </select>
        </div>

        <input type="date" className="input text-sm w-40"
               value={filters.date}
               onChange={e => setFilters(f => ({ ...f, date: e.target.value }))} />

        {(filters.domaine || filters.date || search) && (
          <button className="text-sm text-blue-600 hover:text-blue-800"
                  onClick={() => { setFilters({ domaine: '', date: '' }); setSearch(''); }}>
            Réinitialiser
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading && <div className="progress-bar-indeterminate" />}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                {['ID', 'Étudiant / Sujet', 'Encadrant', 'Examinateur', 'Président', 'Créneau / Salle', 'Scores NLP', ''].map(h => (
                  <th key={h} className="table-th whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-gray-400 text-sm">
                    Aucune affectation. Lancez la génération CSP d'abord.
                  </td>
                </tr>
              )}
              {displayed.map(aff => (
                editId === aff.id ? (
                  <EditRow key={aff.id} aff={aff} profs={profs} creneaux={creneaux}
                           onSave={() => { setEditId(null); load(page); }}
                           onCancel={() => setEditId(null)} />
                ) : (
                  <tr key={aff.id} className="hover:bg-gray-50 transition-colors">
                    <td className="table-td font-mono text-xs text-gray-400">{aff.etudiant?.id}</td>
                    <td className="table-td max-w-xs">
                      <div className="font-medium text-gray-900">
                        {aff.etudiant?.prenom} {aff.etudiant?.nom}
                      </div>
                      <div className="text-xs text-gray-400 truncate">
                        {aff.etudiant?.sujet?.slice(0, 55)}{(aff.etudiant?.sujet?.length ?? 0) > 55 ? '…' : ''}
                      </div>
                      {aff.etudiant?.domaine && (
                        <span className={`badge mt-1 ${DOMAIN_COLORS[aff.etudiant.domaine] || 'bg-gray-100 text-gray-600'}`}>
                          {aff.etudiant.domaine}
                        </span>
                      )}
                    </td>
                    <td className="table-td text-xs whitespace-nowrap">
                      {aff.encadrant?.prenom} {aff.encadrant?.nom}
                      <div className="text-gray-400">{aff.encadrant?.grade}</div>
                    </td>
                    <td className="table-td text-xs whitespace-nowrap">
                      {aff.examinateur?.prenom} {aff.examinateur?.nom}
                      <div className="text-gray-400">{aff.examinateur?.grade}</div>
                    </td>
                    <td className="table-td text-xs whitespace-nowrap">
                      {aff.president?.prenom} {aff.president?.nom}
                      <div className="text-gray-400">{aff.president?.grade}</div>
                    </td>
                    <td className="table-td text-xs whitespace-nowrap">
                      <div className="font-medium">{aff.creneau?.date}</div>
                      <div className="text-gray-400">{aff.creneau?.slot}</div>
                      <div className="text-gray-400">{aff.creneau?.salle}</div>
                    </td>
                    <td className="table-td">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <span>Exam</span>
                          <ScoreBadge score={aff.score_exam} />
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <span>Prés</span>
                          <ScoreBadge score={aff.score_pres} />
                        </div>
                      </div>
                    </td>
                    <td className="table-td">
                      <button onClick={() => setEditId(aff.id)}
                              className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition-colors">
                        <Edit2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
            <p className="text-xs text-gray-500">
              Page {page} sur {pages} — {total} résultats
            </p>
            <div className="flex gap-1">
              <button className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}>
                <ChevronLeft size={14} />
              </button>
              {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                const pg = Math.max(1, Math.min(page - 2, pages - 4)) + i;
                return (
                  <button key={pg}
                          className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                            pg === page ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                          }`}
                          onClick={() => setPage(pg)}>
                    {pg}
                  </button>
                );
              })}
              <button className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => setPage(p => Math.min(pages, p + 1))}
                      disabled={page === pages}>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
