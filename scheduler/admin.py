"""
scheduler/admin.py

Django Admin panel registration.

Flask had NO equivalent — this is a free Django feature.
Visit http://localhost:8000/admin/ after running:

    python manage.py createsuperuser

You get a full CRUD interface for every model — search, filter, pagination,
inline editing — with zero frontend code.

This is extremely useful during development:
    - Inspect the DB after running the scheduler
    - Manually fix a wrong jury assignment
    - Check NLP scores on individual affectations
    - Delete / re-import data without touching the API

How Django admin works
──────────────────────────────────────────────────────────────────────────────
  1. You register a model with admin.site.register(Model, ModelAdmin)
  2. ModelAdmin controls how that model appears in the interface:
       list_display  → columns shown in the list view
       list_filter   → sidebar filter panel
       search_fields → search box (SQL ILIKE query)
       readonly_fields → fields shown but not editable
       inlines       → nested related objects in the detail view
──────────────────────────────────────────────────────────────────────────────
"""

from django.contrib import admin
from .models import Etudiant, Professeur, Creneau, Affectation, UserProfile


# ── Professeur ────────────────────────────────────────────────────────────────

@admin.register(Professeur)
class ProfesseurAdmin(admin.ModelAdmin):
    """
    List view shows the most useful columns for quick scanning.
    search_fields enables the search box — Django generates:
        WHERE nom ILIKE '%query%' OR prenom ILIKE '%query%'
    list_filter adds a sidebar to filter by domaine with one click.
    """

    list_display   = ["id", "nom", "prenom", "domaine", "grade"]
    search_fields  = ["nom", "prenom", "id"]
    list_filter    = ["domaine", "grade"]
    ordering       = ["nom"]

    # Show specialites and disponibilites as read-only formatted text
    # (they are stored as semicolon strings — the list helpers make them readable)
    readonly_fields = ["specialites", "disponibilites"]


# ── Etudiant ──────────────────────────────────────────────────────────────────

@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    """
    encadrant__nom uses Django's __ traversal to display the related
    Professeur's name directly in the list — no extra query needed
    because Django admin calls select_related automatically.
    """

    list_display  = ["id", "nom", "prenom", "domaine", "encadrant", "annee"]
    search_fields = ["nom", "prenom", "id", "sujet"]
    list_filter   = ["domaine", "annee"]
    ordering      = ["domaine", "nom"]

    # raw_id_fields → shows a small popup to pick the encadrant by ID
    # instead of a slow <select> dropdown with all professors
    raw_id_fields = ["encadrant"]


# ── Creneau ───────────────────────────────────────────────────────────────────

@admin.register(Creneau)
class CreneauAdmin(admin.ModelAdmin):
    """
    Useful for verifying that the Excel import created the correct slots.
    list_filter on date lets you click through days quickly.
    """

    list_display  = ["id", "date", "slot", "salle", "capacite"]
    search_fields = ["id", "salle"]
    list_filter   = ["date", "slot"]
    ordering      = ["date", "slot"]


# ── Affectation ───────────────────────────────────────────────────────────────

class AffectationInline(admin.TabularInline):
    """
    Inline view — shown inside the Etudiant detail page.
    Lets you see and edit an etudiant's jury assignment without
    leaving the etudiant form.

    TabularInline → compact horizontal table layout
    StackedInline → vertical stacked layout (better for many fields)
    """

    model  = Affectation
    extra  = 0         # don't show empty rows for adding new affectations
    fields = ["examinateur", "president", "creneau", "score_exam", "score_pres"]

    # FK fields shown as popups (avoids huge dropdowns)
    raw_id_fields = ["examinateur", "president", "creneau"]


@admin.register(Affectation)
class AffectationAdmin(admin.ModelAdmin):
    """
    Main view for inspecting scheduler output.

    score_exam and score_pres are readonly — they are computed by the NLP
    engine and should not be changed manually.

    list_select_related → tells Django admin to do a SELECT with JOINs
    instead of N separate queries when rendering the list.
    This is the admin equivalent of select_related() in views.
    """

    list_display  = [
        "id",
        "etudiant",
        "examinateur",
        "president",
        "creneau",
        "score_exam",
        "score_pres",
    ]
    search_fields = [
        "etudiant__nom",
        "etudiant__prenom",
        "examinateur__nom",
        "president__nom",
    ]
    list_filter       = [
        "creneau__date",
        "etudiant__domaine",
    ]
    readonly_fields       = ["score_exam", "score_pres", "created_at"]
    list_select_related   = True    # avoids N+1 queries in the list view
    raw_id_fields         = ["etudiant", "examinateur", "president", "creneau"]
    ordering              = ["creneau__date", "creneau__slot"]

    # Show the assignment scores prominently at the top of the detail form
    fieldsets = [
        ("Jury",    {"fields": ["etudiant", "examinateur", "president", "creneau"]}),
        ("Scores NLP", {
            "fields":      ["score_exam", "score_pres"],
            "description": "Scores calculés automatiquement par le moteur NLP — lecture seule.",
        }),
        ("Métadonnées", {
            "fields":   ["created_at"],
            "classes":  ["collapse"],   # collapsed by default — less clutter
        }),
    ]


# ── UserProfile ───────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Manage user roles and link users to their domain profiles.
    """

    list_display  = ["user", "role", "professeur", "etudiant"]
    search_fields = ["user__username", "user__email", "role"]
    list_filter   = ["role"]
    ordering      = ["user__username"]

    # Allow editing role and linking to domain models
    fields = ["user", "role", "professeur", "etudiant"]
    readonly_fields = ["user"]  # User field is read-only after creation

    # Use raw_id_fields for professeur and etudiant to avoid dropdown performance issues
    raw_id_fields = ["professeur", "etudiant"]
