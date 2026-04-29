import React, { useState, useEffect } from 'react';
import { getMyEtudiantProfile, updateMyEtudiantProfile, getProfesseurs } from '../auth/api';

const EtudiantProfile = () => {
  const [etudiantData, setEtudiantData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [professeurs, setProfesseurs] = useState([]);
  const [loadingProfesseurs, setLoadingProfesseurs] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    loadEtudiantProfile();
  }, []);

  const loadEtudiantProfile = async () => {
    try {
      setIsLoading(true);
      const response = await getMyEtudiantProfile();
      setEtudiantData(response.data);
      setFormData(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Impossible de charger le profil de l\'étudiant');
      console.error('Error loading student profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProfesseurs = async () => {
    try {
      setLoadingProfesseurs(true);
      const response = await getProfesseurs();
      setProfesseurs(response.data.results || response.data);
    } catch (err) {
      console.error('Error loading professors:', err);
    } finally {
      setLoadingProfesseurs(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError(null);
      const updateData = {
        sujet: formData.sujet || '',
        email: formData.email || '',
        telephone: formData.telephone || '',
        encadrant_id: formData.encadrant_id || ''
      };
      
      const response = await updateMyEtudiantProfile(updateData);
      setEtudiantData(response.data);
      setIsEditing(false);
      setSuccessMessage('Profil mis à jour avec succès');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.response?.data?.error || 'Impossible de mettre à jour le profil');
      console.error('Error updating student profile:', err);
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Chargement...</div>;
  }

  if (!etudiantData) {
    return <div className="text-center py-8 text-red-500">{error || "Aucun profil trouvé"}</div>;
  }

  return (
    <div className="card overflow-hidden">
      <div className="bg-gradient-to-r from-[var(--brand-navy)] to-[var(--brand-sea)] px-6 py-6 text-white">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Profil etudiant</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">
          {etudiantData.prenom} {etudiantData.nom}
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-semibold">
            {etudiantData.domaine}
          </span>
          <span className="rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-semibold">
            Annee {etudiantData.annee || 'non specifiee'}
          </span>
        </div>
      </div>

      {error && (
        <div className="m-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="m-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
          {successMessage}
        </div>
      )}

      <div className="p-6">
        {!isEditing ? (
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Prénom</label>
                <p className="mt-1 text-gray-900">{etudiantData.prenom}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom</label>
                <p className="mt-1 text-gray-900">{etudiantData.nom}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <p className="mt-1 text-gray-900">{etudiantData.email || 'Non défini'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <p className="mt-1 text-gray-900">{etudiantData.telephone || 'Non défini'}</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Domaine d'étude</label>
              <p className="mt-1 text-gray-900">{etudiantData.domaine}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Année</label>
              <p className="mt-1 text-gray-900">{etudiantData.annee || 'Non spécifiée'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Encadrant</label>
              <p className="mt-1 text-gray-900">{etudiantData.encadrant_nom || 'Aucun encadrant'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Sujet de these/PFE</label>
              <div className="card-muted mt-2 p-4">
                <p className="text-gray-900 whitespace-pre-wrap">
                  {etudiantData.sujet || 'Aucun sujet défini'}
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                setIsEditing(true);
                loadProfesseurs();
              }}
              className="btn-primary mt-6"
            >
              Modifier profil
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email || ''}
                  onChange={handleInputChange}
                  className="input mt-1"
                  placeholder="email@exemple.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <input
                  type="text"
                  name="telephone"
                  value={formData.telephone || ''}
                  onChange={handleInputChange}
                  className="input mt-1"
                  placeholder="+33 6 XX XX XX XX"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Sujet de thèse/PFE
              </label>
              <textarea
                name="sujet"
                value={formData.sujet || ''}
                onChange={handleInputChange}
                className="input mt-1 min-h-[140px]"
                placeholder="Decrivez le sujet de votre these ou projet de fin d'etudes..."
                rows="6"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Encadrant
              </label>
              <select
                name="encadrant_id"
                value={formData.encadrant_id || ''}
                onChange={handleInputChange}
                className="select mt-1"
                disabled={loadingProfesseurs}
              >
                <option value="">
                  {loadingProfesseurs ? 'Chargement...' : 'Sélectionnez un encadrant'}
                </option>
                {professeurs.map((prof) => (
                  <option key={prof.id} value={prof.id}>
                    {prof.prenom} {prof.nom} ({prof.domaine})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-3 mt-6">
              <button type="submit" className="btn-primary">
                Enregistrer
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsEditing(false);
                  setFormData(etudiantData);
                  setError(null);
                }}
                className="btn-secondary"
              >
                Annuler
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default EtudiantProfile;
