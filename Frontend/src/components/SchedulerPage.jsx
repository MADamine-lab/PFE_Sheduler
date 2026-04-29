import React, { useState, useEffect, useRef } from 'react';
import { runScheduler, getUploadStatus, getNlpStatus, exportExcel, exportPDF } from '../auth/api';
import toast from 'react-hot-toast';
import {
  Play, Settings2, CheckCircle2, AlertCircle, FileSpreadsheet,
  FileText, Info, Zap, Brain, Cpu, Clock, RefreshCw
} from 'lucide-react';

function ParamSlider({ label, value, min, max, step, onChange, format, description }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-sm font-bold text-blue-700">{format ? format(value) : value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={e => onChange(Number(e.target.value))}
             className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600" />
      {description && <p className="text-xs text-gray-400">{description}</p>}
    </div>
  );
}

function NlpStatusBanner() {
  const [status, setStatus]     = useState(null);
  const [checking, setChecking] = useState(true);
  const pollRef = useRef(null);

  const check = async () => {
    try {
      const r = await getNlpStatus();
      setStatus(r.data);
      if (r.data.ready) {
        clearInterval(pollRef.current);
      }
    } catch {
      setStatus(null);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    check();
    // Poll toutes les 3 s tant que le modèle n'est pas prêt
    pollRef.current = setInterval(check, 3000);
    return () => clearInterval(pollRef.current);
  }, []);

  if (checking && !status) return null;

  if (!status) return null;

  if (!status.ready) {
    return (
      <div className="card p-4 border-amber-200 bg-amber-50 flex items-start gap-3">
        <div className="mt-0.5">
          <RefreshCw size={18} className="text-amber-600 animate-spin" />
        </div>
        <div>
          <p className="text-sm font-semibold text-amber-800">Modèle BERT en cours de chargement…</p>
          <p className="text-xs text-amber-700 mt-1">
            Le modèle se télécharge/charge en arrière-plan (~471 Mo, une seule fois).
            Vous pouvez lancer la génération — elle attendra automatiquement que le modèle soit prêt.
          </p>
          <div className="progress-bar-indeterminate mt-2" />
        </div>
      </div>
    );
  }

  const isBert = status.mode === 'bert';
  return (
    <div className={`card p-3 flex items-center gap-3 ${isBert ? 'border-green-200 bg-green-50' : 'border-blue-100 bg-blue-50'}`}>
      {isBert
        ? <Brain size={18} className="text-green-600 flex-shrink-0" />
        : <Cpu   size={18} className="text-blue-600 flex-shrink-0" />}
      <div>
        <p className={`text-sm font-semibold ${isBert ? 'text-green-800' : 'text-blue-800'}`}>
          {isBert ? 'BERT multilingue actif' : 'TF-IDF + synonymes actif'}
        </p>
        <p className={`text-xs ${isBert ? 'text-green-600' : 'text-blue-600'}`}>
          {isBert
            ? 'paraphrase-multilingual-MiniLM-L12-v2 — matching sémantique précis'
            : 'Fallback — installez torch + sentence-transformers pour BERT'}
        </p>
      </div>
      <span className={`ml-auto badge ${isBert ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
        Prêt
      </span>
    </div>
  );
}

export default function SchedulerPage() {
  const [dbStatus, setDbStatus]   = useState(null);
  const [params, setParams]       = useState({ nlp_threshold: 0.10, max_jury_per_day: 4 });
  const [running, setRunning]     = useState(false);
  const [elapsed, setElapsed]     = useState(0);
  const [result, setResult]       = useState(null);
  const [exporting, setExporting] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    getUploadStatus().then(r => setDbStatus(r.data)).catch(() => {});
  }, []);

  // Chronomètre pendant la génération
  useEffect(() => {
    if (running) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [running]);

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await runScheduler(params);
      setResult(res.data);
      toast.success(res.data.message);
    } catch (e) {
      toast.error(e.message || 'Erreur lors de la génération');
    } finally {
      setRunning(false);
    }
  };

  const handleExport = async (type) => {
    setExporting(type);
    try {
      if (type === 'excel') await exportExcel();
      else await exportPDF();
      toast.success(`Export ${type.toUpperCase()} téléchargé`);
    } catch { toast.error(`Erreur export ${type}`); }
    finally { setExporting(''); }
  };

  const ready = dbStatus && dbStatus.etudiants > 0 && dbStatus.professeurs > 0;
  const taux  = result ? Math.round((result.stats.resolved / result.stats.total) * 100) : 0;

  const fmtTime = s => `${Math.floor(s / 60)}m ${s % 60}s`;

  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Generation</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Generation CSP</h1>
        <p className="mt-2 text-sm text-white/75">
          Configurez les parametres puis lancez l'algorithme d'affectation.
        </p>
      </div>

      {/* Statut modèle NLP */}
      <NlpStatusBanner />

      {/* Statut données */}
      {dbStatus && (
        <div className={`card p-4 flex items-start gap-3 ${ready ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
          {ready
            ? <CheckCircle2 size={18} className="text-green-600 mt-0.5" />
            : <AlertCircle  size={18} className="text-amber-600 mt-0.5" />}
          <div>
            <p className={`text-sm font-medium ${ready ? 'text-green-800' : 'text-amber-800'}`}>
              {ready ? 'Données prêtes' : 'Données manquantes — importez un fichier d\'abord'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {dbStatus.etudiants} étudiants · {dbStatus.professeurs} professeurs · {dbStatus.creneaux} créneaux
            </p>
          </div>
        </div>
      )}

      {/* Explication algorithme */}
      <div className="card p-5 border-blue-100 bg-blue-50">
        <div className="flex items-center gap-2 mb-3 text-blue-800">
          <Info size={16} />
          <p className="text-sm font-semibold">Pipeline d'affectation</p>
        </div>
        <ol className="text-xs text-blue-700 space-y-1.5">
          {[
            ['1','BERT batch','Calcule la similarité sémantique sujet↔spécialités pour tous les profs en une passe.'],
            ['2','Élagage','Supprime les profs sous le seuil NLP, non disponibles, ou encadrants de l\'étudiant.'],
            ['3','Backtracking','Essaie les combinaisons examinateur+président. Forward-checking détecte les impasses tôt.'],
            ['4','Min-Conflicts','Choisit le créneau qui équilibre la charge journalière de chaque jury.'],
          ].map(([n,t,d]) => (
            <li key={n} className="flex gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-200 text-blue-800 flex items-center justify-center text-xs font-bold">{n}</span>
              <span><strong>{t}</strong> — {d}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Paramètres */}
      <div className="card p-6 space-y-5">
        <div className="flex items-center gap-2 text-gray-800">
          <Settings2 size={18} />
          <h2 className="font-semibold">Paramètres CSP</h2>
        </div>
        <ParamSlider
          label="Seuil NLP minimum"
          value={params.nlp_threshold}
          min={0.0} max={0.50} step={0.01}
          onChange={v => setParams(p => ({ ...p, nlp_threshold: v }))}
          format={v => `${(v * 100).toFixed(0)}%`}
          description="Score de similarité cosinus minimum. 0% = tous les profs éligibles (recommandé avec BERT)."
        />
        <ParamSlider
          label="Max soutenances / prof / jour"
          value={params.max_jury_per_day}
          min={1} max={8} step={1}
          onChange={v => setParams(p => ({ ...p, max_jury_per_day: v }))}
          description="Limite la surcharge journalière de chaque jury."
        />
      </div>

      {/* Bouton lancer */}
      <button className="btn-primary w-full py-3.5 text-base"
              onClick={handleRun} disabled={!ready || running}>
        {running ? (
          <span className="flex items-center justify-center gap-3">
            <div className="spinner border-white border-t-transparent" />
            <span>
              Génération en cours…&nbsp;
              <span className="font-mono text-blue-200">{fmtTime(elapsed)}</span>
            </span>
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Zap size={18} /> Lancer la génération
          </span>
        )}
      </button>

      {running && (
        <div className="space-y-1">
          <div className="progress-bar-indeterminate" />
          <p className="text-xs text-gray-400 text-center">
            {elapsed < 15
              ? 'Calcul des embeddings BERT…'
              : elapsed < 60
              ? 'Résolution CSP — backtracking en cours…'
              : 'Sauvegarde des affectations…'}
          </p>
        </div>
      )}

      {/* Résultat */}
      {result && (
        <div className="space-y-4">
          <div className="card p-5 border-green-200 bg-green-50">
            <div className="flex items-center gap-2 text-green-800 mb-4">
              <CheckCircle2 size={20} />
              <p className="font-semibold text-lg">{result.message}</p>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { label: 'Total', value: result.stats.total, color: 'text-gray-800' },
                { label: 'Résolus', value: result.stats.resolved, color: 'text-green-700' },
                { label: 'Non résolus', value: result.stats.unresolved,
                  color: result.stats.unresolved > 0 ? 'text-red-600' : 'text-gray-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-white rounded-lg p-3 text-center border border-green-100">
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
              ))}
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-green-700">
                <span>Taux de réussite</span>
                <span className="font-bold">{taux}%</span>
              </div>
              <div className="w-full bg-green-100 rounded-full h-2.5">
                <div className="bg-green-600 h-2.5 rounded-full" style={{ width: `${taux}%` }} />
              </div>
            </div>
            {result.unresolved?.length > 0 && (
              <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-100">
                <p className="text-xs font-medium text-red-700 mb-1">
                  Étudiants sans affectation ({result.unresolved.length}) :
                </p>
                <p className="text-xs text-red-600 font-mono">{result.unresolved.join(' · ')}</p>
                <p className="text-xs text-red-500 mt-1">
                  Baissez le seuil NLP à 0% ou ajoutez des créneaux disponibles.
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button className="btn-secondary flex items-center justify-center gap-2 py-3"
                    onClick={() => handleExport('excel')} disabled={exporting === 'excel'}>
              {exporting === 'excel'
                ? <><div className="spinner" /> Export…</>
                : <><FileSpreadsheet size={18} className="text-green-600" /> Export Excel</>}
            </button>
            <button className="btn-secondary flex items-center justify-center gap-2 py-3"
                    onClick={() => handleExport('pdf')} disabled={exporting === 'pdf'}>
              {exporting === 'pdf'
                ? <><div className="spinner" /> Export…</>
                : <><FileText size={18} className="text-red-600" /> Export PDF</>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
