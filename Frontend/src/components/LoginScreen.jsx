import { useState } from 'react'

function EmailIcon({ className }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  )
}

function KeyIcon({ className }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="7.5" cy="15.5" r="5.5" />
      <path d="m21 2-3 3" />
      <path d="M18.5 4.5 22 8" />
      <path d="M12.5 10.5 19 4" />
    </svg>
  )
}

/** Logo institutionnel (remplacez `logoSrc` par le chemin de votre fichier logo ISSAT si besoin) */
function IssatLogo({ logoSrc, className = '' }) {
  if (logoSrc) {
    return (
      <img
        src={logoSrc}
        alt="ISSAT Sousse"
        className={`mx-auto h-20 w-auto object-contain ${className}`}
      />
    )
  }
  return (
    <div
      className={`mx-auto flex max-w-[280px] flex-col items-center gap-2 ${className}`}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#0c4a6e] shadow-md ring-2 ring-[#0c4a6e]/20">
        <span className="text-lg font-bold tracking-tight text-white">ISSAT</span>
      </div>
      <p className="text-center text-xs font-semibold uppercase tracking-wide text-[#0c4a6e]">
        Institut Supérieur des Sciences Appliquées et de Technologie
      </p>
      <p className="text-sm font-medium text-slate-600">Sousse</p>
    </div>
  )
}

const inputShell =
  'flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm transition focus-within:border-[var(--brand-sea)] focus-within:ring-2 focus-within:ring-[var(--brand-sea)]/20'

const iconClass = 'h-5 w-5 shrink-0 text-[#0c4a6e]/70'

/** Écran de connexion — style sobre inspiré de l’identité institutionnelle ISSAT Sousse. */
export default function LoginScreen({
  logoSrc,
  loginError,
  onSubmit,
  onForgotPassword,
  onRegister,
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    Promise.resolve(onSubmit?.({ email, password })).then((errorMessage) => {
      if (errorMessage) {
        setError(errorMessage)
      }
    })
  }

  return (
    <div className="min-h-screen">
      <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
        <section className="relative overflow-hidden bg-[var(--brand-navy)] text-white">
          <div className="absolute -top-24 right-0 h-64 w-64 rounded-full bg-[var(--brand-gold)]/30 blur-3xl" />
          <div className="absolute bottom-0 left-0 h-72 w-72 rounded-full bg-[var(--brand-sea)]/40 blur-3xl" />
          <div className="relative z-10 flex h-full flex-col justify-between px-8 py-10 sm:px-12">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--brand-gold)] text-[var(--brand-navy)] text-lg font-bold">
                  UIT
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/70">Plateforme PFE</p>
                  <p className="text-lg font-semibold">Universite Internationale de Tunis</p>
                </div>
              </div>
              <h1 className="mt-8 text-3xl font-semibold leading-tight text-white sm:text-4xl">
                Pilotez vos soutenances avec une experience fluide et moderne.
              </h1>
              <p className="mt-4 max-w-md text-sm text-white/75">
                Suivi des jurys, planning et dossiers etudiants dans un espace unifie,
                inspire de l'esthetique institutionnelle UIT.
              </p>
            </div>

            <div className="mt-10 grid gap-4">
              {[
                {
                  label: 'Planification intelligente',
                  detail: 'CSP + NLP pour equilibrer jurys, disponibilites et sujets.',
                },
                {
                  label: 'Suivi en temps reel',
                  detail: 'Tableaux de bord et exports pour vos equipes.',
                },
                {
                  label: 'Experience unifiee',
                  detail: 'Espace admin, etudiant et professeur sur une seule interface.',
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur"
                >
                  <p className="text-sm font-semibold text-white">{item.label}</p>
                  <p className="mt-1 text-xs text-white/70">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-10 sm:px-10">
          <div className="w-full max-w-md">
            <div className="card p-8 sm:p-10">
              <IssatLogo logoSrc={logoSrc} className="mb-8" />

              <header className="mb-8 text-center">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                  Connexion securisee
                </p>
                <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-[1.7rem]">
                  Accedez a votre espace
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 sm:text-[0.95rem]">
                  Connectez-vous pour gerer vos soutenances et votre planning.
                </p>
              </header>

              {(loginError || error) ? (
                <div
                  className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                  role="alert"
                >
                  {error || loginError}
                </div>
              ) : null}

              <form className="space-y-5" onSubmit={handleSubmit} noValidate>
                <div>
                  <label
                    htmlFor="login-email"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Email
                  </label>
                  <div className={inputShell}>
                    <EmailIcon className={iconClass} />
                    <input
                      id="login-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="nom.prenom@uit.tn"
                      className="min-w-0 flex-1 border-0 bg-transparent text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="login-password"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Mot de passe
                  </label>
                  <div className={inputShell}>
                    <KeyIcon className={iconClass} />
                    <input
                      id="login-password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="min-w-0 flex-1 border-0 bg-transparent text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
                    />
                  </div>
                </div>

                <button type="submit" className="btn-primary w-full py-3 text-sm">
                  Se connecter
                </button>
              </form>

              <div className="mt-6 text-center">
                <button
                  type="button"
                  onClick={onForgotPassword}
                  className="text-sm font-medium text-[var(--brand-sea)] underline-offset-4 hover:underline"
                >
                  Mot de passe oublie ?
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
