"""
scheduler/views.py

DRF API views — replaces three Flask route files:
    routes/upload.py    →  UploadView, UploadStatusView
    routes/scheduler.py →  RunSchedulerView, AffectationListView,
                           AffectationDetailView, ProfesseurListView,
                           CreneauListView
    routes/stats.py     →  DashboardView

Flask used Blueprint + @bp.route() decorators.
Django REST Framework uses class-based APIView (or generics).

Why class-based views?
──────────────────────────────────────────────────────────────────────────────
Flask:   @scheduler_bp.route("/run", methods=["POST"])
         def run_scheduler(): ...

DRF:     class RunSchedulerView(APIView):
             def post(self, request): ...

Benefits for React integration:
  - Each HTTP method (get/post/put/delete) is its own method → no if/else on request.method
  - request.data already parsed (JSON or multipart) — no request.get_json()
  - return Response(data, status=...) — no jsonify(), no make_response()
  - Exceptions raise → DRF catches and returns proper JSON error responses
  - Pagination, authentication, throttling wired in automatically
──────────────────────────────────────────────────────────────────────────────
"""

import os
import logging
from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Etudiant, Professeur, Creneau, Affectation, UserProfile
from .serializers import (
    AffectationSerializer,
    AffectationUpdateSerializer,
    ProfesseurSerializer,
    ProfesseurWriteSerializer,
    EtudiantSerializer,
    EtudiantUpdateSerializer,
    CreneauSerializer,
    UploadSummarySerializer,
    SchedulerResultSerializer,
    DashboardSerializer,
)

logger = logging.getLogger("scheduler")


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD
#  Flask: routes/upload.py
#  Endpoints:
#    POST /api/upload/          ← replaces @upload_bp.route("/", methods=["POST"])
#    GET  /api/upload/status/   ← replaces @upload_bp.route("/status", methods=["GET"])
# ══════════════════════════════════════════════════════════════════════════════

class UploadView(APIView):
    """
    Accepts an Excel or CSV file, parses it, persists to DB.

    Flask used:
        file = request.files["file"]
        file.save(save_path)

    DRF equivalent:
        file = request.FILES["file"]        ← request.FILES, not request.files
        with open(save_path, "wb") as f:
            for chunk in file.chunks(): f.write(chunk)

    MultiPartParser lets DRF handle multipart/form-data (the encoding
    that React's FormData uses when uploading files).
    """

    # Tell DRF this view accepts file uploads
    parser_classes = [MultiPartParser, FileUploadParser]

    def post(self, request):
        # ── 1. Validate file presence and extension ────────────────────────────
        if "file" not in request.FILES:
            return Response(
                {"error": "Aucun fichier envoyé"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]

        if not file.name:
            return Response(
                {"error": "Nom de fichier vide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in [".xlsx", ".xls", ".csv"]:
            return Response(
                {"error": "Format non supporté. Utilisez .xlsx, .xls ou .csv"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 2. Save file to disk ───────────────────────────────────────────────
        # Flask: save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], ...)
        # Django: settings.UPLOAD_FOLDER defined in settings.py
        from django.conf import settings
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        save_path = os.path.join(settings.UPLOAD_FOLDER, "current" + ext)

        with open(save_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # ── 3. Parse file ──────────────────────────────────────────────────────
        from services.file_parser import parse_excel_file, generate_default_creneaux
        etudiants, professeurs, creneaux, errors = parse_excel_file(save_path)

        if errors:
            # Flask: return jsonify({"errors": errors}), 422
            return Response(
                {"errors": errors, "warnings": []},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        warnings = []
        if not creneaux:
            creneaux = generate_default_creneaux()
            warnings.append("Feuille 'Creneaux' absente — créneaux par défaut générés (09-20 juin 2025)")

        # ── 4. Persist to DB inside a transaction ──────────────────────────────
        # Flask used multiple try/except with db.session.rollback()
        # Django: transaction.atomic() rolls back everything if any step fails
        try:
            with transaction.atomic():
                # Clear existing data (same order as Flask version to respect FK constraints)
                Affectation.objects.all().delete()
                Etudiant.objects.all().delete()
                Professeur.objects.all().delete()
                Creneau.objects.all().delete()

                # Insert professors
                for p in professeurs:
                    Professeur.objects.update_or_create(
                        id=str(p.get("id") or p.get("prof_id", "")).strip(),
                        defaults={
                            "nom":           str(p.get("nom", "")).strip(),
                            "prenom":        str(p.get("prenom", "")).strip(),
                            "domaine":       str(p.get("domaine", "")).strip(),
                            "specialites":   str(p.get("specialites", "")).strip(),
                            "grade":         str(p.get("grade", "")).strip(),
                            "disponibilites":str(p.get("disponibilites", "")).strip(),
                        },
                    )

                # Insert students
                for e in etudiants:
                    enc_id = str(e.get("encadrant_id", "")).strip()
                    try:
                        encadrant = Professeur.objects.get(id=enc_id)
                    except Professeur.DoesNotExist:
                        logger.warning("Encadrant %s introuvable pour étudiant %s", enc_id, e.get("etudiant_id"))
                        continue

                    Etudiant.objects.update_or_create(
                        id=str(e.get("etudiant_id", "")).strip(),
                        defaults={
                            "nom":      str(e.get("nom", "")).strip(),
                            "prenom":   str(e.get("prenom", "")).strip(),
                            "domaine":  str(e.get("domaine", "")).strip(),
                            "sujet":    str(e.get("sujet", "")).strip(),
                            "encadrant":encadrant,
                            "annee":    str(e.get("annee", "")).strip(),
                        },
                    )

                # Insert time slots
                for c in creneaux:
                    Creneau.objects.update_or_create(
                        id=str(c.get("id") or c.get("creneau_id", "")).strip(),
                        defaults={
                            "date":     str(c.get("date", "")).strip(),
                            "slot":     str(c.get("slot", "")).strip(),
                            "salle":    str(c.get("salle", "")).strip(),
                            "capacite": int(c.get("capacite", 1)),
                        },
                    )

        except Exception as exc:
            logger.exception("Erreur lors de l'import du fichier")
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 5. Return summary ──────────────────────────────────────────────────
        # Flask: return jsonify({...}), 200
        # DRF:   return Response({...}, status=HTTP_200_OK)
        return Response(
            {
                "message":  "Fichier importé avec succès",
                "warnings": warnings,
                "summary": {
                    "etudiants":   len(etudiants),
                    "professeurs": len(professeurs),
                    "creneaux":    len(creneaux),
                },
            },
            status=status.HTTP_200_OK,
        )


class UploadStatusView(APIView):
    """
    GET /api/upload/status/
    Replaces @upload_bp.route("/status", methods=["GET"])

    Flask:  return jsonify({"etudiants": n, ...})
    DRF:    return Response({"etudiants": n, ...})
    """

    def get(self, request):
        return Response({
            "etudiants":   Etudiant.query.count()   if False else Etudiant.objects.count(),
            "professeurs": Professeur.objects.count(),
            "creneaux":    Creneau.objects.count(),
        })


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEDULER
#  Flask: routes/scheduler.py
#  Endpoints:
#    POST /api/scheduler/run/
#    GET  /api/scheduler/affectations/
#    PUT  /api/scheduler/affectations/<id>/
#    GET  /api/scheduler/professeurs/
#    GET  /api/scheduler/creneaux/
# ══════════════════════════════════════════════════════════════════════════════

class RunSchedulerView(APIView):
    """
    POST /api/scheduler/run/
    Replaces @scheduler_bp.route("/run", methods=["POST"])

    The CSP engine (csp_scheduler.py) is unchanged — we just call it differently.

    Flask:  body = request.get_json(silent=True) or {}
    DRF:    body = request.data   ← already parsed, always a dict
    """

    def post(self, request):
        body      = request.data
        threshold = float(body.get("nlp_threshold", 0.10))
        max_jury  = int(body.get("max_jury_per_day", 4))

        # ── Validate data exists ───────────────────────────────────────────────
        etudiants_qs   = Etudiant.objects.select_related("encadrant").all()
        professeurs_qs = Professeur.objects.all()
        creneaux_qs    = Creneau.objects.all()

        if not etudiants_qs.exists():
            return Response(
                {"error": "Aucun étudiant en base. Importez d'abord un fichier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not professeurs_qs.exists():
            return Response({"error": "Aucun professeur en base."}, status=status.HTTP_400_BAD_REQUEST)
        if not creneaux_qs.exists():
            return Response({"error": "Aucun créneau en base."}, status=status.HTTP_400_BAD_REQUEST)

        # ── Flatten to dicts for the CSP engine ───────────────────────────────
        # csp_scheduler.py expects plain dicts — same format as Flask version
        def prof_flat(p):
            return {
                "id": p.id, "nom": p.nom, "prenom": p.prenom,
                "domaine": p.domaine,
                "specialites": p.specialites_list(),
                "disponibilites": p.disponibilites,
            }

        def etu_flat(e):
            return {
                "id": e.id, "nom": e.nom, "prenom": e.prenom,
                "domaine": e.domaine, "sujet": e.sujet,
                "encadrant_id": e.encadrant_id,
            }

        def cr_flat(c):
            return {"id": c.id, "date": c.date, "slot": c.slot, "salle": c.salle}

        etudiants   = [etu_flat(e) for e in etudiants_qs]
        professeurs = [prof_flat(p) for p in professeurs_qs]
        creneaux    = [cr_flat(c) for c in creneaux_qs]

        logger.info(
            "run: %d etu | %d profs | %d créneaux | seuil=%.2f | max_jury=%d",
            len(etudiants), len(professeurs), len(creneaux), threshold, max_jury,
        )

        # ── Run CSP engine (unchanged service) ────────────────────────────────
        try:
            from services.csp_scheduler import PFEScheduler
            import services.csp_scheduler as csp_mod
            csp_mod.MAX_JURY_PER_DAY = max_jury

            engine = PFEScheduler()
            result = engine.run(etudiants, professeurs, creneaux, nlp_threshold=threshold)
        except Exception as exc:
            logger.exception("Erreur moteur CSP")
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ── Persist results ────────────────────────────────────────────────────
        # Flask used manual db.session.add() in a loop with individual try/except.
        # Django: bulk_create inside atomic() is faster and safer.
        saved = 0
        try:
            with transaction.atomic():
                Affectation.objects.all().delete()

                affectations_to_create = []
                for aff in result.get("affectations", []):
                    try:
                        affectations_to_create.append(Affectation(
                            etudiant_id    = aff["etudiant_id"],
                            examinateur_id = aff["examinateur_id"],
                            president_id   = aff["president_id"],
                            creneau_id     = aff["creneau_id"],
                            score_exam     = float(aff.get("score_exam", 0.0)),
                            score_pres     = float(aff.get("score_pres", 0.0)),
                        ))
                    except Exception as exc:
                        logger.error("Erreur préparation affectation %s: %s", aff.get("etudiant_id"), exc)

                # bulk_create inserts all rows in a single SQL statement — much
                # faster than individual .save() calls in Flask's loop
                Affectation.objects.bulk_create(affectations_to_create)
                saved = len(affectations_to_create)

        except Exception as exc:
            logger.exception("Erreur sauvegarde affectations")
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info("%d affectations sauvegardées", saved)

        return Response(
            {
                "message":    f"{saved} affectations générées",
                "stats":      result["stats"],
                "unresolved": [u["id"] for u in result.get("unresolved", [])],
            },
            status=status.HTTP_200_OK,
        )


class AffectationPagination(PageNumberPagination):
    """
    Custom pagination for the affectations list.

    Flask had manual  page / per_page  logic:
        query.offset((page-1) * per_page).limit(per_page).all()

    DRF handles all of this automatically.
    React receives:
        { count, next, previous, results: [...] }
    """
    page_size             = 20
    page_size_query_param = "per_page"   # React can send ?per_page=50
    max_page_size         = 200


class AffectationListView(APIView):
    """
    GET /api/scheduler/affectations/
    Replaces @scheduler_bp.route("/affectations", methods=["GET"])

    Flask manually joined tables for filtering.
    Django ORM uses  .filter()  with double-underscore traversal across FK relations.

    Flask:  query.join(Etudiant).filter(Etudiant.domaine == domaine)
    Django: Affectation.objects.filter(etudiant__domaine=domaine)
    """

    def get(self, request):
        domaine     = request.query_params.get("domaine", "").strip()
        date_filter = request.query_params.get("date", "").strip()

        # select_related → single SQL JOIN instead of N+1 queries
        # (same as SQLAlchemy's joinedload)
        qs = Affectation.objects.select_related(
            "etudiant__encadrant",
            "examinateur",
            "president",
            "creneau",
        )

        # Flask: query.filter(Etudiant.domaine == domaine)
        # Django: __ traverses the FK relation
        if domaine:
            qs = qs.filter(etudiant__domaine=domaine)
        if date_filter:
            qs = qs.filter(creneau__date=date_filter)

        # Paginate
        paginator   = AffectationPagination()
        page        = paginator.paginate_queryset(qs, request)
        serializer  = AffectationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AffectationDetailView(APIView):
    """
    PUT /api/scheduler/affectations/<id>/
    Replaces @scheduler_bp.route("/affectations/<int:aff_id>", methods=["PUT"])

    Validation is now handled by AffectationUpdateSerializer.validate()
    instead of inline if/return blocks.
    """

    def put(self, request, pk):
        # Flask: aff = Affectation.query.get_or_404(aff_id)
        # Django: get_object_or_404 is the direct equivalent
        aff = get_object_or_404(Affectation, pk=pk)

        serializer = AffectationUpdateSerializer(
            aff,
            data=request.data,
            partial=True,    # partial=True → only update fields present in request body
        )

        if serializer.is_valid():
            serializer.save()
            # Return the full updated affectation using the read serializer
            return Response(AffectationSerializer(aff).data)

        # Validation failed → DRF returns the error dict from .validate()
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfesseurListView(APIView):
    """
    GET /api/scheduler/professeurs/
    Replaces @scheduler_bp.route("/professeurs", methods=["GET"])
    """

    def get(self, request):
        domaine = request.query_params.get("domaine", "").strip()
        qs = Professeur.objects.all()
        if domaine:
            qs = qs.filter(domaine=domaine)
        serializer = ProfesseurSerializer(qs, many=True)
        return Response(serializer.data)


class CreneauListView(APIView):
    """
    GET /api/scheduler/creneaux/
    Replaces @scheduler_bp.route("/creneaux", methods=["GET"])
    """

    def get(self, request):
        qs         = Creneau.objects.order_by("date", "slot")
        serializer = CreneauSerializer(qs, many=True)
        return Response(serializer.data)


# ══════════════════════════════════════════════════════════════════════════════
#  STATS
#  Flask: routes/stats.py
#  Endpoints:
#    GET /api/stats/dashboard/
# ══════════════════════════════════════════════════════════════════════════════

class DashboardView(APIView):
    """
    GET /api/stats/dashboard/
    Replaces @stats_bp.route("/dashboard", methods=["GET"])

    Flask used raw SQLAlchemy queries:
        db.session.query(Etudiant.domaine, db.func.count(...)).group_by(...).all()

    Django ORM equivalent uses  .values()  +  .annotate()  for aggregations.
    """

    def get(self, request):
        from django.db.models import Count, Avg

        # ── Counts ─────────────────────────────────────────────────────────────
        # Flask: Etudiant.query.count()
        # Django: Etudiant.objects.count()
        counts = {
            "etudiants":   Etudiant.objects.count(),
            "professeurs": Professeur.objects.count(),
            "affectations":Affectation.objects.count(),
            "creneaux":    Creneau.objects.count(),
        }

        # ── Students per domain ────────────────────────────────────────────────
        # Flask: db.session.query(Etudiant.domaine, func.count()).group_by(...).all()
        # Django: .values("domaine").annotate(count=Count("id"))
        by_domain = list(
            Etudiant.objects
            .values("domaine")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # ── Jury load (nb of assignments per professor) ────────────────────────
        # Flask computed exam_loads and pres_loads separately then merged manually.
        # Django: we annotate both relations directly.
        exam_load = {
            row["examinateur_id"]: row["c"]
            for row in Affectation.objects
                .values("examinateur_id")
                .annotate(c=Count("id"))
        }
        pres_load = {
            row["president_id"]: row["c"]
            for row in Affectation.objects
                .values("president_id")
                .annotate(c=Count("id"))
        }

        jury_load_map = defaultdict(int)
        for pid, cnt in exam_load.items():
            jury_load_map[pid] += cnt
        for pid, cnt in pres_load.items():
            jury_load_map[pid] += cnt

        prof_map = {p.id: f"{p.prenom} {p.nom}" for p in Professeur.objects.all()}
        jury_load = sorted(
            [{"prof": prof_map.get(pid, pid), "count": cnt} for pid, cnt in jury_load_map.items()],
            key=lambda x: -x["count"],
        )[:20]

        # ── Assignments per date ───────────────────────────────────────────────
        by_date = list(
            Affectation.objects
            .values("creneau__date")
            .annotate(count=Count("id"))
            .order_by("creneau__date")
        )
        by_date = [{"date": row["creneau__date"], "count": row["count"]} for row in by_date]

        # ── Average NLP scores ─────────────────────────────────────────────────
        # Flask: db.session.query(func.avg(Affectation.score_exam), ...).first()
        # Django: .aggregate(Avg("score_exam"), Avg("score_pres"))
        avg = Affectation.objects.aggregate(
            avg_exam=Avg("score_exam"),
            avg_pres=Avg("score_pres"),
        )
        avg_nlp = {
            "examinateur": round(avg["avg_exam"] or 0, 3),
            "president":   round(avg["avg_pres"] or 0, 3),
        }

        return Response({
            "counts":        counts,
            "by_domain":     by_domain,
            "jury_load":     jury_load,
            "by_date":       by_date,
            "avg_nlp_scores":avg_nlp,
        })

class NlpStatusView(APIView):
    """
    GET /api/nlp/status/
    Retourne le statut du modèle NLP (BERT ou fallback)
    """
    permission_classes = [AllowAny]  # Ou IsAuthenticated selon vos besoins
    
    def get(self, request):
        # Importer le module de vérification NLP
        from services.nlp_utils import get_nlp_status
        
        status = get_nlp_status()
        return Response(status)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("=== LOGIN DEBUG ===")
        print("request.data:", request.data)
        print("Content-Type:", request.content_type)
    
        identifier = request.data.get("email") or request.data.get("username")
        password = request.data.get("password")
    
        print("identifier:", identifier)
        print("password:", password)
        if not identifier or not password:
            return Response({"error": "Email et mot de passe requis."}, status=status.HTTP_400_BAD_REQUEST)

        # Allow email or username login
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                if not user_obj.check_password(password):
                    raise User.DoesNotExist
                user = user_obj
            except User.DoesNotExist:
                return Response({"error": "Identifiants invalides."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Utilisateur inactif."}, status=status.HTTP_403_FORBIDDEN)

        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': 'admin' if user.is_superuser else 'prof' if user.is_staff else 'etudiant'}
        )

        token, created = Token.objects.get_or_create(user=user)

        response = Response({
            "detail": "Authentification réussie",
            "username": user.username,
            "email": user.email,
            "role": profile.role,
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
        })

        response.set_cookie(
            "auth_token",
            token.key,
            httponly=True,
            secure=request.is_secure(),
            samesite="Lax",
            max_age=60 * 60 * 24 * 7,
        )

        return response

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.auth
        if token is not None:
            token.delete()

        response = Response({"detail": "Déconnexion réussie"})
        response.delete_cookie("auth_token")
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = user.profile
            role = profile.role
        except UserProfile.DoesNotExist:
            # Fallback to old logic if profile doesn't exist
            role = 'admin' if user.is_superuser else 'prof' if user.is_staff else 'etudiant'

        return Response({
            "username": user.username,
            "email": user.email,
            "role": role,
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
        })


# ══════════════════════════════════════════════════════════════════════════════
#  PROFESSEUR PROFILE
#  Endpoints:
#    GET  /api/professeur/<id>/    ← get teacher profile
#    PUT  /api/professeur/<id>/    ← update teacher profile
#    GET  /api/me/professeur/      ← get current user's teacher profile
# ══════════════════════════════════════════════════════════════════════════════

class ProfesseurDetailView(APIView):
    """
    GET  /api/professeur/<id>/   — Retrieve a single professor
    PUT  /api/professeur/<id>/   — Update professor profile (email, phone, specialties, availability)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, prof_id):
        """Get professor profile"""
        try:
            prof = Professeur.objects.get(id__iexact=prof_id)
        except Professeur.DoesNotExist:
            return Response(
                {"error": "Professeur non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProfesseurSerializer(prof)
        return Response(serializer.data)

    def put(self, request, prof_id):
        """Update professor profile"""
        try:
            prof = Professeur.objects.get(id__iexact=prof_id)
        except Professeur.DoesNotExist:
            return Response(
                {"error": "Professeur non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use ProfesseurWriteSerializer to handle PUT data
        serializer = ProfesseurWriteSerializer(prof, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full serializer data including computed fields
            return Response(
                ProfesseurSerializer(prof).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyProfesseurView(APIView):
    """
    GET  /api/me/professeur/     — Get current user's professor profile
    PUT  /api/me/professeur/     — Update current user's professor profile
    
    Searches for a Professeur by matching with user's email or username
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's professor profile"""
        user = request.user
        
        # Try to find by email first, then by username
        prof = None
        try:
            # Try to match by email
            prof = Professeur.objects.get(email__iexact=user.email)
        except Professeur.DoesNotExist:
            try:
                # Try to match by ID (case-insensitive, username might be the professor ID)
                prof = Professeur.objects.get(id__iexact=user.username)
            except Professeur.DoesNotExist:
                pass
        
        if not prof:
            return Response(
                {"error": "Aucun profil professeur trouvé pour cet utilisateur"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProfesseurSerializer(prof)
        return Response(serializer.data)

    def put(self, request):
        """Update current user's professor profile"""
        user = request.user
        
        # Try to find by email first, then by username
        prof = None
        try:
            prof = Professeur.objects.get(email__iexact=user.email)
        except Professeur.DoesNotExist:
            try:
                prof = Professeur.objects.get(id__iexact=user.username)
            except Professeur.DoesNotExist:
                pass
        
        if not prof:
            return Response(
                {"error": "Aucun profil professeur trouvé pour cet utilisateur"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProfesseurWriteSerializer(prof, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                ProfesseurSerializer(prof).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyProfesseurSpaceView(APIView):
    """
    GET  /api/me/professeur/espace/ — Return professor profile + supervised students

    This powers the teacher space UI with the professor summary and the list of
    students supervised by this professor.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        prof = None
        try:
            prof = Professeur.objects.get(email__iexact=user.email)
        except Professeur.DoesNotExist:
            try:
                prof = Professeur.objects.get(id__iexact=user.username)
            except Professeur.DoesNotExist:
                pass

        if not prof:
            return Response(
                {"error": "Aucun profil professeur trouvé pour cet utilisateur"},
                status=status.HTTP_404_NOT_FOUND,
            )

        etudiants = prof.etudiants_encadres.select_related("encadrant").all()

        return Response(
            {
                "profile": ProfesseurSerializer(prof).data,
                "stats": {
                    "etudiants": etudiants.count(),
                    "specialites": len(prof.specialites_list()),
                    "disponibilites": len(prof.disponibilites_list()),
                },
                "etudiants": [
                    {
                        "id": e.id,
                        "nom": e.nom,
                        "prenom": e.prenom,
                        "domaine": e.domaine,
                        "sujet": e.sujet,
                        "annee": e.annee,
                        "email": e.email,
                        "telephone": e.telephone,
                    }
                    for e in etudiants
                ],
            },
            status=status.HTTP_200_OK,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  ETUDIANT PROFILE
#  Endpoints:
#    GET  /api/etudiant/<id>/     ← get student profile
#    PUT  /api/etudiant/<id>/     ← update student profile
#    GET  /api/me/etudiant/       ← get current user's student profile
# ══════════════════════════════════════════════════════════════════════════════

class EtudiantDetailView(APIView):
    """
    GET  /api/etudiant/<id>/     — Retrieve a single student
    PUT  /api/etudiant/<id>/     — Update student profile (subject, email, phone)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, etudiant_id):
        """Get student profile"""
        try:
            etudiant = Etudiant.objects.get(id__iexact=etudiant_id)
        except Etudiant.DoesNotExist:
            return Response(
                {"error": "Étudiant non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = EtudiantSerializer(etudiant)
        return Response(serializer.data)

    def put(self, request, etudiant_id):
        """Update student profile"""
        try:
            etudiant = Etudiant.objects.get(id__iexact=etudiant_id)
        except Etudiant.DoesNotExist:
            return Response(
                {"error": "Étudiant non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # For student updates, we need custom logic for encadrant_id
        serializer = EtudiantUpdateSerializer(etudiant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full serializer data
            return Response(
                EtudiantSerializer(etudiant).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyEtudiantView(APIView):
    """
    GET  /api/me/etudiant/       — Get current user's student profile
    PUT  /api/me/etudiant/       — Update current user's student profile
    
    Searches for an Etudiant by matching with user's email or username
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's student profile"""
        user = request.user
        
        # Try to find by email first, then by username
        etudiant = None
        try:
            # Try to match by email
            etudiant = Etudiant.objects.get(email__iexact=user.email)
        except Etudiant.DoesNotExist:
            try:
                # Try to match by ID (case-insensitive, username might be the student ID)
                etudiant = Etudiant.objects.get(id__iexact=user.username)
            except Etudiant.DoesNotExist:
                pass
        
        if not etudiant:
            return Response(
                {"error": "Aucun profil étudiant trouvé pour cet utilisateur"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = EtudiantSerializer(etudiant)
        return Response(serializer.data)

    def put(self, request):
        """Update current user's student profile"""
        user = request.user
        
        # Try to find by email first, then by username
        etudiant = None
        try:
            etudiant = Etudiant.objects.get(email__iexact=user.email)
        except Etudiant.DoesNotExist:
            try:
                etudiant = Etudiant.objects.get(id__iexact=user.username)
            except Etudiant.DoesNotExist:
                pass
        
        if not etudiant:
            return Response(
                {"error": "Aucun profil étudiant trouvé pour cet utilisateur"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = EtudiantUpdateSerializer(etudiant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                EtudiantSerializer(etudiant).data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════════════
#  DATA INSPECTION & ACCOUNT CREATION
#  Test endpoints to view existing data and create user accounts
# ══════════════════════════════════════════════════════════════════════════════

class DataView(APIView):
    """
    GET /api/data/ — Show all existing etudiants, professeurs, and users
    
    Useful for:
      - Inspecting what data exists in the database
      - Testing with real data from MySQL
      - Debugging user/profile matching
    """
    permission_classes = [AllowAny]  # Allow inspection without authentication

    def get(self, request):
        """Return all etudiants, professeurs, and users"""
        etudiants = Etudiant.objects.select_related("encadrant").all()
        professeurs = Professeur.objects.all()
        users = User.objects.all()
        
        return Response({
            "etudiants": [
                {
                    "id": e.id,
                    "nom": e.nom,
                    "prenom": e.prenom,
                    "sujet": e.sujet,
                    "encadrant_id": e.encadrant.id if e.encadrant else "",
                    "encadrant_nom": f"{e.encadrant.prenom} {e.encadrant.nom}" if e.encadrant else "",
                    "email": e.email,
                    "telephone": e.telephone,
                    "domaine": e.domaine,
                }
                for e in etudiants
            ],
            "professeurs": [
                {
                    "id": p.id,
                    "nom": p.nom,
                    "prenom": p.prenom,
                    "email": p.email,
                    "telephone": p.telephone,
                    "domaine": p.domaine,
                    "grade": p.grade,
                }
                for p in professeurs
            ],
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                }
                for u in users
            ],
            "counts": {
                "etudiants": etudiants.count(),
                "professeurs": professeurs.count(),
                "users": users.count(),
            }
        }, status=status.HTTP_200_OK)


class CreateAccountsView(APIView):
    """
    POST /api/create-accounts/ — Auto-create Django user accounts
    
    Creates a user account for each etudiant and professeur.
    If they don't have an email, generates one based on their ID and name.
    
    Usage:
      - If record has email: uses email as username
      - If record has NO email: generates email from ID (e.g., e0120@example.com)
    
    All accounts use default password: password123
    """
    permission_classes = [AllowAny]  # Allow account creation without authentication

    def post(self, request):
        """Create user accounts for all etudiants and professeurs"""
        created_accounts = []
        skipped = []
        errors = []
        
        default_password = "password123"
        
        # Create accounts for etudiants
        for etudiant in Etudiant.objects.all():
            try:
                # Determine username and email:
                # - If email exists: use email as username
                # - If no email: use ID as username, generate dummy email
                if etudiant.email.strip():
                    email = etudiant.email.strip()
                    username = email.lower()
                else:
                    # Use ID as username, generate dummy email
                    username = etudiant.id.lower()
                    email = f"{etudiant.id.lower()}@uniproject.local"
                
                # Check if user already exists
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": etudiant.prenom,
                        "last_name": etudiant.nom,
                    }
                )

                # Ensure user profile role is etudiant
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"role": "etudiant"}
                )
                if profile.role != "etudiant":
                    profile.role = "etudiant"
                    profile.save()
                
                if created:
                    # Set password only for new users
                    user.set_password(default_password)
                    user.save()
                    created_accounts.append({
                        "type": "etudiant",
                        "id": etudiant.id,
                        "name": f"{etudiant.prenom} {etudiant.nom}",
                        "username": username,
                        "email": email,
                        "password": default_password,
                        "status": "created"
                    })
                else:
                    created_accounts.append({
                        "type": "etudiant",
                        "id": etudiant.id,
                        "name": f"{etudiant.prenom} {etudiant.nom}",
                        "username": username,
                        "email": email,
                        "status": "already_exists"
                    })
            except Exception as e:
                errors.append({
                    "type": "etudiant",
                    "id": etudiant.id,
                    "name": f"{etudiant.prenom} {etudiant.nom}",
                    "error": str(e)
                })
        
        # Create accounts for professeurs
        for professeur in Professeur.objects.all():
            try:
                # Determine username and email (same logic as etudiants)
                if professeur.email.strip():
                    email = professeur.email.strip()
                    username = email.lower()
                else:
                    # Use ID as username, generate dummy email
                    username = professeur.id.lower()
                    email = f"{professeur.id.lower()}@uniproject.local"
                
                # Check if user already exists
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": professeur.prenom,
                        "last_name": professeur.nom,
                    }
                )

                # Ensure professor accounts are staff and have prof role
                if not user.is_staff and not user.is_superuser:
                    user.is_staff = True
                    user.save()

                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"role": "prof"}
                )
                if profile.role != "prof":
                    profile.role = "prof"
                    profile.save()
                
                if created:
                    # Set password only for new users
                    user.set_password(default_password)
                    user.save()
                    created_accounts.append({
                        "type": "professeur",
                        "id": professeur.id,
                        "name": f"{professeur.prenom} {professeur.nom}",
                        "username": username,
                        "email": email,
                        "password": default_password,
                        "status": "created"
                    })
                else:
                    created_accounts.append({
                        "type": "professeur",
                        "id": professeur.id,
                        "name": f"{professeur.prenom} {professeur.nom}",
                        "username": username,
                        "email": email,
                        "status": "already_exists"
                    })
            except Exception as e:
                errors.append({
                    "type": "professeur",
                    "id": professeur.id,
                    "name": f"{professeur.prenom} {professeur.nom}",
                    "error": str(e)
                })
        
        return Response({
            "message": "Account creation process completed",
            "created_accounts": created_accounts,
            "skipped": skipped,
            "errors": errors,
            "summary": {
                "total_created": len([a for a in created_accounts if a.get("status") == "created"]),
                "total_already_exists": len([a for a in created_accounts if a.get("status") == "already_exists"]),
                "total_skipped": len(skipped),
                "total_errors": len(errors),
            }
        }, status=status.HTTP_201_CREATED)
