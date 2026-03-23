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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.pagination import PageNumberPagination

from .models import Etudiant, Professeur, Creneau, Affectation
from .serializers import (
    AffectationSerializer,
    AffectationUpdateSerializer,
    ProfesseurSerializer,
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