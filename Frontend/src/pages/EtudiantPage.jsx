import React from 'react';
import EtudiantProfile from '../components/EtudiantProfile';

const EtudiantPage = () => {
  return (
    <div className="page-shell space-y-6">
      <div className="page-hero">
        <p className="text-xs uppercase tracking-[0.3em] text-white/70">Espace etudiant</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Votre dossier PFE</h1>
        <p className="mt-2 text-sm text-white/75">
          Consultez vos informations et mettez a jour votre profil.
        </p>
      </div>

      <EtudiantProfile />
    </div>
  );
};

export default EtudiantPage;