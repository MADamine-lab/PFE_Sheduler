import React from 'react';
import ProfesseurProfile from '../components/ProfesseurProfile';

const ProfPage = () => {
  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Espace professeur</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Votre espace enseignant</h1>
        <p className="mt-2 text-sm text-white/75">
          Suivez vos encadrements, specialites et disponibilites.
        </p>
      </div>

      <ProfesseurProfile />
    </div>
  );
};

export default ProfPage;