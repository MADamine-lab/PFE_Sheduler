"""
pfe_project/urls.py

Top-level URL router.

Flask equivalent — what you had in __init__.py :
    app.register_blueprint(upload_bp,    url_prefix="/api/upload")
    app.register_blueprint(scheduler_bp, url_prefix="/api/scheduler")
    app.register_blueprint(export_bp,    url_prefix="/api/export")
    app.register_blueprint(stats_bp,     url_prefix="/api/stats")

In Django there is no Blueprint concept.
Instead, each app owns its own urls.py and we include() them here.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # ── Django admin panel ─────────────────────────────────────────────────────
    # Free, zero-config. Visit http://localhost:8000/admin/
    # Create a superuser with:  python manage.py createsuperuser
    path("admin/", admin.site.urls),
    path("api/", include("scheduler.urls")),
    # ── DRF browsable API auth (login/logout buttons in the browser UI) ────────
    # Only useful during development — lets you test endpoints in the browser
    # without Postman or React being ready yet.
    path("api-auth/", include("rest_framework.urls")),

    # ── Our app routes ─────────────────────────────────────────────────────────
    # Each include() delegates to scheduler/urls.py for the actual view mapping.
    #
    # Flask blueprint          →  Django include()
    # ─────────────────────────────────────────────
    # /api/upload/             →  scheduler/urls.py  (UploadView)
    # /api/scheduler/run       →  scheduler/urls.py  (RunSchedulerView)
    # /api/scheduler/affectations → scheduler/urls.py (AffectationView)
    # /api/export/excel        →  scheduler/urls.py  (ExportExcelView)
    # /api/export/pdf          →  scheduler/urls.py  (ExportPdfView)
    # /api/stats/dashboard     →  scheduler/urls.py  (DashboardView)
    #
    # We use a single "api/" prefix and let scheduler/urls.py handle the rest.
    path("api/", include("scheduler.urls")),

]


# ── Serve uploaded files in development ───────────────────────────────────────
# In Flask, uploaded files were served automatically from UPLOAD_FOLDER.
# In Django, media files need this extra line during development.
# In production, your web server (Nginx / Caddy) serves MEDIA_ROOT directly.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)