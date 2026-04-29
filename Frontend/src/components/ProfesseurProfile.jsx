import React, { useState, useEffect } from 'react';
import { getMyProfesseurProfile, updateMyProfesseurProfile, getMyProfesseurSpace } from '../auth/api';
import { Users, BookOpen, CalendarDays } from 'lucide-react';

const ProfesseurProfile = () => {
  const [profData, setProfData] = useState(null);
  const [spaceData, setSpaceData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    loadProfesseurProfile();
  }, []);

  const normalizeFormData = (data) => ({
    ...data,
    specialites: Array.isArray(data?.specialites)
      ? data.specialites.join('; ')
      : (data?.specialites || ''),
    disponibilites: Array.isArray(data?.disponibilites)
      ? data.disponibilites.join('; ')
      : (data?.disponibilites || ''),
  });

  const loadProfesseurProfile = async () => {
    try {
      setIsLoading(true);
      const [profileResponse, spaceResponse] = await Promise.all([
        getMyProfesseurProfile(),
        getMyProfesseurSpace(),
      ]);

      setProfData(profileResponse.data);
      setSpaceData(spaceResponse.data);
      setFormData(normalizeFormData(profileResponse.data));
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Impossible de charger le profil du professeur');
      console.error('Error loading professor profile:', err);
    } finally {
      setIsLoading(false);
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
        email: formData.email || '',
        telephone: formData.telephone || '',
        specialites: formData.specialites || '',
        disponibilites: formData.disponibilites || '',
        grade: formData.grade || ''
      };
      
      const response = await updateMyProfesseurProfile(updateData);
      setProfData(response.data);
      setIsEditing(false);
      setSuccessMessage('Profil mis à jour avec succès');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.response?.data?.error || 'Impossible de mettre à jour le profil');
      console.error('Error updating professor profile:', err);
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Chargement...</div>;
  }

  if (!profData) {
    return <div className="text-center py-8 text-red-500">{error || "Aucun profil trouvé"}</div>;
  }

  const supervisedStudents = spaceData?.etudiants || [];
  const stats = spaceData?.stats || { etudiants: 0, specialites: 0, disponibilites: 0 };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-[var(--brand-navy)] via-[#123a5a] to-[var(--brand-sea)] rounded-2xl shadow-lg text-white p-8">
        <p className="text-sm text-blue-100 uppercase tracking-widest">Espace enseignant</p>
        <h2 className="text-3xl font-bold mt-2">{profData.prenom} {profData.nom}</h2>
        <p className="text-blue-100 mt-2">{profData.domaine} · {profData.grade || 'Grade non défini'}</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 text-sm text-blue-100">
              <Users size={16} /> Étudiants encadrés
            </div>
            <p className="text-2xl font-bold mt-2">{stats.etudiants}</p>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 text-sm text-blue-100">
              <BookOpen size={16} /> Spécialités
            </div>
            <p className="text-2xl font-bold mt-2">{stats.specialites}</p>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 text-sm text-blue-100">
              <CalendarDays size={16} /> Disponibilités
            </div>
            <p className="text-2xl font-bold mt-2">{stats.disponibilites}</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">Mon profil</h3>
          <p className="text-gray-600 mt-1">Informations personnelles et professionnelles</p>
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
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Prénom</label>
                <p className="mt-1 text-gray-900">{profData.prenom}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom</label>
                <p className="mt-1 text-gray-900">{profData.nom}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <p className="mt-1 text-gray-900">{profData.email || 'Non défini'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <p className="mt-1 text-gray-900">{profData.telephone || 'Non défini'}</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Grade</label>
              <p className="mt-1 text-gray-900">{profData.grade || 'Non défini'}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Spécialités</label>
              <div className="mt-1">
                {Array.isArray(profData.specialites) && profData.specialites.length > 0 ? (
                  <ul className="list-disc list-inside text-gray-900">
                    {profData.specialites.map((spec, idx) => (
                      <li key={idx}>{spec}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-900">Aucune spécialité</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Disponibilités</label>
              <div className="mt-1">
                {Array.isArray(profData.disponibilites) && profData.disponibilites.length > 0 ? (
                  <ul className="list-disc list-inside text-gray-900">
                    {profData.disponibilites.map((dispo, idx) => (
                      <li key={idx}>{dispo}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-900">Aucune disponibilité</p>
                )}
              </div>
            </div>

            <button
              onClick={() => setIsEditing(true)}
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
              <label className="block text-sm font-medium text-gray-700">Grade</label>
              <input
                type="text"
                name="grade"
                value={formData.grade || ''}
                onChange={handleInputChange}
                className="input mt-1"
                placeholder="Professeur, Maitre de conferences, etc."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Spécialités (séparées par un point-virgule)
              </label>
              <textarea
                name="specialites"
                value={formData.specialites || ''}
                onChange={handleInputChange}
                className="input mt-1 min-h-[110px]"
                placeholder="Specialite 1; Specialite 2; Specialite 3"
                rows="3"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Disponibilités (séparées par un point-virgule)
              </label>
              <textarea
                name="disponibilites"
                value={formData.disponibilites || ''}
                onChange={handleInputChange}
                className="input mt-1 min-h-[110px]"
                placeholder="2025-06-09 matin; 2025-06-10 apres-midi; ..."
                rows="3"
              />
              <p className="mt-1 text-xs text-gray-500">Format: YYYY-MM-DD matin/après-midi/journée</p>
            </div>

            <div className="flex gap-3 mt-6">
              <button type="submit" className="btn-primary">
                Enregistrer
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsEditing(false);
                  setFormData(normalizeFormData(profData));
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

      <div className="card">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Étudiants encadrés</h3>
            <p className="text-gray-600 mt-1">Liste des étudiants sous votre supervision</p>
          </div>
          <div className="text-sm text-blue-700 bg-blue-50 px-3 py-2 rounded-lg">
            {supervisedStudents.length} étudiant(s)
          </div>
        </div>

        <div className="p-6 overflow-x-auto">
          {supervisedStudents.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="py-3 pr-4 font-medium">Étudiant</th>
                  <th className="py-3 pr-4 font-medium">Domaine</th>
                  <th className="py-3 pr-4 font-medium">Sujet</th>
                  <th className="py-3 pr-4 font-medium">Année</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {supervisedStudents.map((student) => (
                  <tr key={student.id}>
                    <td className="py-4 pr-4 font-medium text-gray-900">{student.prenom} {student.nom}</td>
                    <td className="py-4 pr-4 text-gray-700">{student.domaine}</td>
                    <td className="py-4 pr-4 text-gray-700 max-w-xl whitespace-pre-wrap">{student.sujet || 'Aucun sujet renseigné'}</td>
                    <td className="py-4 pr-4 text-gray-700">{student.annee || 'Non spécifiée'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-400 text-center py-10">Aucun étudiant encadré pour le moment</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfesseurProfile;
