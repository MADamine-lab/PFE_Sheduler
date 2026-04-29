/** Comptes de démonstration uniquement — à remplacer par une vraie API. */
export const TEST_ACCOUNTS = [
  { email: 'admin@demo.local', password: 'demo123', role: 'admin' },
  { email: 'etudiant@demo.local', password: 'demo123', role: 'etudiant' },
  { email: 'prof@demo.local', password: 'demo123', role: 'prof' },
]

export function matchTestAccount(email, password) {
  const normalized = email.trim().toLowerCase()
  return (
    TEST_ACCOUNTS.find(
      (a) => a.email === normalized && a.password === password
    ) ?? null
  )
}
