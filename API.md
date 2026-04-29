# API Reference

Base URL: /api/

## Auth
- GET /auth/csrf/ - get CSRF token (cookie + json)
- POST /auth/login/ - login with { email or username, password }
- POST /auth/logout/ - logout and clear auth cookie
- GET /auth/me/ - get current user info (role, username, email)

## Upload
- POST /upload/ - upload Excel or CSV file (multipart form-data, file key: file)
- GET /upload/status/ - check last upload status

## Scheduler
- POST /scheduler/run/ - run scheduler
- GET /scheduler/affectations/ - list affectations (supports filters: domaine, date, page, per_page)
- PUT /scheduler/affectations/<id>/ - update affectation (examinateur_id, president_id, creneau_id)
- GET /scheduler/professeurs/ - list professeurs (filter: domaine)
- GET /scheduler/creneaux/ - list creneaux

## Export
- GET /export/excel/ - download planning as Excel
- GET /export/pdf/ - download planning as PDF

## Stats
- GET /stats/dashboard/ - dashboard summary (counts, by_domain, jury_load, by_date, avg_nlp_scores)

## Professeur
- GET /professeur/<id>/ - get professor profile
- PUT /professeur/<id>/ - update professor profile
- GET /me/professeur/ - get current professor profile
- PUT /me/professeur/ - update current professor profile
- GET /me/professeur/espace/ - professor space (profile + supervised students)

## Etudiant
- GET /etudiant/<id>/ - get student profile
- PUT /etudiant/<id>/ - update student profile
- GET /me/etudiant/ - get current student profile
- PUT /me/etudiant/ - update current student profile

## Data and account tools (testing)
- GET /data/ - list etudiants, professeurs, users, counts
- POST /create-accounts/ - create accounts for etudiants and professeurs (default password: password123)
