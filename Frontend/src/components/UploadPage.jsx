import React, { useState, useRef, useCallback } from 'react';
import { uploadFile, getUploadStatus } from '../auth/api';
import toast from 'react-hot-toast';
import { Upload, FileSpreadsheet, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';

export default function UploadPage() {
  const [dragging, setDragging] = useState(false);
  const [file, setFile]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult]     = useState(null);
  const [errors, setErrors]     = useState([]);
  const inputRef = useRef();

  const handleFile = useCallback((f) => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['xlsx','xls','csv'].includes(ext)) {
      toast.error('Format non supporté. Utilisez .xlsx, .xls ou .csv');
      return;
    }
    setFile(f);
    setResult(null);
    setErrors([]);
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onInputChange = (e) => {
    const f = e.target.files[0];
    if (f) handleFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(0);
    setErrors([]);
    try {
      const res = await uploadFile(file, setProgress);
      setResult(res.data);
      toast.success(`${res.data.summary.etudiants} étudiants importés avec succès`);
    } catch (e) {
      const errData = e.message;
      setErrors(typeof errData === 'string' ? [errData] : ['Erreur lors de l\'import']);
      toast.error('Erreur d\'import — vérifiez le fichier');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Import</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Importer les donnees</h1>
        <p className="mt-2 text-sm text-white/75">
          Chargez votre fichier Excel (.xlsx) contenant les feuilles Etudiants, Professeurs et Creneaux.
        </p>
      </div>

      {/* Format guide */}
      <div className="card p-4 border-blue-100 bg-blue-50">
        <div className="flex items-start gap-2">
          <Info size={16} className="text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800 space-y-1">
            <p className="font-medium">Structure attendue du fichier Excel :</p>
            <p><span className="font-medium">Feuille "Etudiants" :</span> etudiant_id · nom · prenom · domaine · sujet · encadrant_id</p>
            <p><span className="font-medium">Feuille "Professeurs" :</span> prof_id · nom · prenom · domaine · specialites · disponibilites</p>
            <p><span className="font-medium">Feuille "Creneaux" :</span> creneau_id · date · slot · salle <span className="text-blue-500">(optionnel)</span></p>
            <p className="text-blue-600 text-xs mt-1">
              Format disponibilités : "2025-06-10 matin; 2025-06-11 après-midi"
            </p>
          </div>
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={`card-muted border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer
          ${dragging ? 'border-[var(--brand-sea)] bg-blue-50' : 'border-gray-200 hover:border-[var(--brand-sea)]/60 hover:bg-white'}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".xlsx,.xls,.csv"
               className="hidden" onChange={onInputChange} />
        <div className="flex flex-col items-center gap-3">
          {file ? (
            <>
              <FileSpreadsheet size={40} className="text-green-500" />
              <div>
                <p className="font-medium text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024).toFixed(1)} Ko
                </p>
              </div>
              <button className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                onClick={e => { e.stopPropagation(); setFile(null); setResult(null); }}>
                <X size={12} /> Supprimer
              </button>
            </>
          ) : (
            <>
              <Upload size={40} className="text-gray-300" />
              <div>
                <p className="font-medium text-gray-700">Glissez votre fichier ici</p>
                <p className="text-sm text-gray-400">ou cliquez pour parcourir</p>
                <p className="text-xs text-gray-400 mt-1">.xlsx · .xls · .csv — max 32 Mo</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Progress */}
      {loading && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Envoi en cours…</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all"
                 style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <div className="card p-4 border-red-200 bg-red-50">
          <div className="flex items-center gap-2 text-red-700 mb-2">
            <AlertTriangle size={16} />
            <p className="font-medium text-sm">Erreurs de validation</p>
          </div>
          <ul className="space-y-1">
            {errors.map((e, i) => (
              <li key={i} className="text-sm text-red-600">• {e}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Success result */}
      {result && (
        <div className="card p-5 border-green-200 bg-green-50">
          <div className="flex items-center gap-2 text-green-700 mb-3">
            <CheckCircle size={18} />
            <p className="font-semibold">Import réussi</p>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Étudiants', value: result.summary.etudiants },
              { label: 'Professeurs', value: result.summary.professeurs },
              { label: 'Créneaux', value: result.summary.creneaux },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white rounded-lg p-3 text-center border border-green-100">
                <p className="text-2xl font-bold text-green-800">{value}</p>
                <p className="text-xs text-green-600">{label}</p>
              </div>
            ))}
          </div>
          {result.warnings?.length > 0 && (
            <div className="mt-3 flex items-start gap-2 text-amber-700">
              <AlertTriangle size={14} className="mt-0.5" />
              <ul className="text-xs space-y-0.5">
                {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
          <p className="text-xs text-green-600 mt-3">
            Rendez-vous sur l'onglet <strong>Génération CSP</strong> pour lancer l'affectation.
          </p>
        </div>
      )}

      {/* Upload button */}
      <div>
        <button className="btn-primary w-full py-3 text-base"
                onClick={handleUpload}
                disabled={!file || loading}>
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="spinner border-white border-t-transparent" /> Import en cours…
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Upload size={18} /> Importer le fichier
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
