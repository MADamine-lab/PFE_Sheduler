"""
scheduler/urls.py

URL routing for the scheduler app.

Flask equivalent — route decorators spread across 4 files:
    @upload_bp.route("/", methods=["POST"])
    @upload_bp.route("/status", methods=["GET"])
    @scheduler_bp.route("/run", methods=["POST"])
    @scheduler_bp.route("/affectations", methods=["GET"])
    @scheduler_bp.route("/affectations/<int:aff_id>", methods=["PUT"])
    @scheduler_bp.route("/professeurs", methods=["GET"])
    @scheduler_bp.route("/creneaux", methods=["GET"])
    @export_bp.route("/excel", methods=["GET"])
    @export_bp.route("/pdf", methods=["GET"])
    @stats_bp.route("/dashboard", methods=["GET"])

In Django, ALL routes live here in one place.
The top-level pfe_project/urls.py delegates everything under /api/ to this file.
So the full URL is:  /api/ + the path() defined below.

──────────────────────────────────────────────────────────────────────────────
Flask route               →  Full Django URL
──────────────────────────────────────────────────────────────────────────────
POST /api/upload/          →  path("upload/", UploadView.as_view())
GET  /api/upload/status/   →  path("upload/status/", UploadStatusView.as_view())
POST /api/scheduler/run/   →  path("scheduler/run/", RunSchedulerView.as_view())
GET  /api/scheduler/affectations/         →  AffectationListView
PUT  /api/scheduler/affectations/<id>/    →  AffectationDetailView
GET  /api/scheduler/professeurs/          →  ProfesseurListView
GET  /api/scheduler/creneaux/             →  CreneauListView
GET  /api/export/excel/    →  path("export/excel/", ExportExcelView.as_view())
GET  /api/export/pdf/      →  path("export/pdf/",   ExportPdfView.as_view())
GET  /api/stats/dashboard/ →  path("stats/dashboard/", DashboardView.as_view())
──────────────────────────────────────────────────────────────────────────────

Key concept — .as_view()
────────────────────────
Flask used function-based views (def run_scheduler():).
DRF uses class-based views (class RunSchedulerView(APIView):).
.as_view() converts the class into a callable that Django's URL router understands.
You never call it yourself — Django calls it on every incoming request.
"""

from django.urls import path

from .views import (
    UploadView,
    UploadStatusView,
    RunSchedulerView,
    AffectationListView,
    AffectationDetailView,
    ProfesseurListView,
    CreneauListView,
    DashboardView,
)
from .export import ExportExcelView, ExportPdfView


urlpatterns = [

    # ── Upload ─────────────────────────────────────────────────────────────────
    # React sends:  POST http://localhost:8000/api/upload/
    #               Content-Type: multipart/form-data
    #               Body: FormData with key "file"
    path("upload/",        UploadView.as_view(),       name="upload"),
    path("upload/status/", UploadStatusView.as_view(), name="upload-status"),

    # ── Scheduler ──────────────────────────────────────────────────────────────
    # React sends:  POST http://localhost:8000/api/scheduler/run/
    #               Content-Type: application/json
    #               Body: { "nlp_threshold": 0.10, "max_jury_per_day": 4 }
    path("scheduler/run/",                    RunSchedulerView.as_view(),      name="scheduler-run"),

    # React sends:  GET http://localhost:8000/api/scheduler/affectations/
    #               Query params: ?domaine=Informatique&date=2025-06-09&page=1&per_page=20
    path("scheduler/affectations/",           AffectationListView.as_view(),   name="affectation-list"),

    # React sends:  PUT http://localhost:8000/api/scheduler/affectations/42/
    #               Body: { "examinateur_id": "PROF007" }
    # <int:pk> captures the numeric ID from the URL → passed as pk to the view
    path("scheduler/affectations/<int:pk>/",  AffectationDetailView.as_view(), name="affectation-detail"),

    # React sends:  GET http://localhost:8000/api/scheduler/professeurs/?domaine=Informatique
    path("scheduler/professeurs/",            ProfesseurListView.as_view(),    name="professeur-list"),

    # React sends:  GET http://localhost:8000/api/scheduler/creneaux/
    path("scheduler/creneaux/",               CreneauListView.as_view(),       name="creneau-list"),

    # ── Export ─────────────────────────────────────────────────────────────────
    # React sends:  GET http://localhost:8000/api/export/excel/
    #               Response: application/vnd.openxmlformats... (file download)
    path("export/excel/", ExportExcelView.as_view(), name="export-excel"),

    # React sends:  GET http://localhost:8000/api/export/pdf/
    #               Response: application/pdf (file download)
    path("export/pdf/",   ExportPdfView.as_view(),   name="export-pdf"),

    # ── Stats ──────────────────────────────────────────────────────────────────
    # React sends:  GET http://localhost:8000/api/stats/dashboard/
    #               Response: { counts, by_domain, jury_load, by_date, avg_nlp_scores }
    path("stats/dashboard/", DashboardView.as_view(), name="stats-dashboard"),
]
