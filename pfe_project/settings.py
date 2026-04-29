"""
pfe_project/settings.py

Django settings for the PFE Scheduler project.
Stack : Django 4.2 + Django REST Framework + React (separate dev server)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()   # reads .env file at project root

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ───────────────────────────────────────────────────────────────────
# In Flask you did:  app.config["SECRET_KEY"] = "..."
# In Django it lives here. Always keep it in .env in production.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-in-production")

# Set to False in production and list your real domain in ALLOWED_HOSTS
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# ── Installed apps ─────────────────────────────────────────────────────────────
# Flask had no concept of "apps" — you registered Blueprints.
# Django uses INSTALLED_APPS. Each entry activates models, migrations, admin, etc.
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",          # free admin panel at /admin/
    "django.contrib.auth",           # user model + authentication
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",                # Django REST Framework
    "rest_framework.authtoken",      # token-based auth (needed later for React login)
    "corsheaders",                   # allow React dev server (port 5173 / 3000) to call the API

    # Our app — replaces all Flask Blueprints
    "scheduler",
]


# ── Middleware ─────────────────────────────────────────────────────────────────
# Flask used @app.before_request / @app.after_request for cross-cutting concerns.
# Django middleware is declared here in order — each layer wraps the next.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",        # must be FIRST
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]

CSRF_COOKIE_HTTPONLY = False   # must be False so JS can read it
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "csrftoken"

# ── URL configuration ──────────────────────────────────────────────────────────
# This is the top-level router.
# Flask equivalent: app.register_blueprint(upload_bp, url_prefix="/api/upload")
ROOT_URLCONF = "pfe_project.urls"


# ── Templates ─────────────────────────────────────────────────────────────────
# We are building a pure API — React handles all rendering.
# We still need this block so Django admin works.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pfe_project.wsgi.application"


# ── Database ───────────────────────────────────────────────────────────────────
# Flask used SQLAlchemy with a separate db = SQLAlchemy(app) object.
# Django has its own ORM built in — just configure the engine here.
#
# SQLite for development (zero config, file-based):
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
#
# ── Switch to PostgreSQL in production ──
# Uncomment and fill .env variables:
#
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME":     os.getenv("DB_NAME", "pfe_db"),
#         "USER":     os.getenv("DB_USER", "postgres"),
#         "PASSWORD": os.getenv("DB_PASSWORD", ""),
#         "HOST":     os.getenv("DB_HOST", "localhost"),
#         "PORT":     os.getenv("DB_PORT", "5432"),
#     }
# }


# ── Password validation (kept at Django defaults) ─────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = "fr-fr"   # matches your French field names (nom, prénom, domaine…)
TIME_ZONE     = "Africa/Tunis"
USE_I18N      = True
USE_TZ        = True


# ── Static files ──────────────────────────────────────────────────────────────
# React will handle the frontend — these settings are only for Django admin assets.
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # collected by `manage.py collectstatic`


# ── Media files (uploaded Excel / CSV) ────────────────────────────────────────
# Flask used:  app.config["UPLOAD_FOLDER"] = "uploads/"
# Django equivalent:
MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"          # uploaded files land here
UPLOAD_FOLDER = MEDIA_ROOT / "uploads"  # referenced in upload view


# ── Default primary key type ───────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  DJANGO REST FRAMEWORK                                                      ║
# ║  Flask had no equivalent — DRF adds serializers, ViewSets,                 ║
# ║  authentication classes, pagination, and a browsable API UI.                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
REST_FRAMEWORK = {

    # ── Rendering ──────────────────────────────────────────────────────────────
    # JSONRenderer      → always available (used by React)
    # BrowsableAPIRenderer → gives you the interactive HTML UI at every endpoint
    #                        very useful during development; disable in production
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],

    # ── Parsing ────────────────────────────────────────────────────────────────
    # JSONParser     → React sends JSON bodies
    # MultiPartParser + FileUploadParser → needed for the Excel/CSV upload endpoint
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FileUploadParser",
    ],

    # ── Authentication ─────────────────────────────────────────────────────────
    # SessionAuthentication → Django admin / browser sessions
    # CookieTokenAuthentication → token stored in HttpOnly cookie 'auth_token'
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "scheduler.authentication.CookieTokenAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],

    # ── Permissions ────────────────────────────────────────────────────────────
    # IsAuthenticated → every API endpoint requires a logged-in user by default.
    # Switch to AllowAny during early development if you don't need auth yet.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",   # ← change to IsAuthenticated later
    ],

    # ── Pagination ─────────────────────────────────────────────────────────────
    # Flask had manual  page / per_page  logic in get_affectations().
    # DRF handles it automatically when you set this.
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,

    # ── Throttling (rate limiting) ─────────────────────────────────────────────
    # Optional — uncomment to protect the /run endpoint from being hammered
    # "DEFAULT_THROTTLE_CLASSES": [
    #     "rest_framework.throttling.AnonRateThrottle",
    #     "rest_framework.throttling.UserRateThrottle",
    # ],
    # "DEFAULT_THROTTLE_RATES": {
    #     "anon": "20/day",
    #     "user": "100/day",
    # },
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CORS — allow React dev server to call the Django API                       ║
# ║  Flask used Flask-CORS with  CORS(app, origins=["http://localhost:5173"])   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173", 
    "http://localhost:5174",  # Vite (React default)
    "http://localhost:3000",   # Create React App
]

# Allow cookies / Authorization header to be sent cross-origin
CORS_ALLOW_CREDENTIALS = True

# In production replace the list above with your real frontend domain:
# CORS_ALLOWED_ORIGINS = ["https://pfe-scheduler.example.com"]


# ── Logging ────────────────────────────────────────────────────────────────────
# Mirrors the  logging.getLogger(__name__)  calls in your Flask services.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "scheduler": {          # logs from our app
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "services": {           # logs from csp_scheduler, nlp_matcher
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}