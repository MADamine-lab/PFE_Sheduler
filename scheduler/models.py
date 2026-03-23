"""
scheduler/models.py

Django ORM models — replaces models/models.py (SQLAlchemy version).

Key differences vs SQLAlchemy
──────────────────────────────────────────────────────────────────────────────
| SQLAlchemy (Flask)                  | Django ORM                           |
|─────────────────────────────────────|──────────────────────────────────────|
| db = SQLAlchemy(app)                | built-in, no setup needed            |
| db.Model                            | models.Model                         |
| db.Column(db.String(80))            | models.CharField(max_length=80)      |
| db.Column(db.Text)                  | models.TextField()                   |
| db.Column(db.Integer)               | models.IntegerField()                |
| db.Column(db.Float)                 | models.FloatField()                  |
| db.Column(db.DateTime)              | models.DateTimeField()               |
| db.ForeignKey("table.col")          | models.ForeignKey(Model, ...)        |
| db.relationship(...)                | defined via ForeignKey itself        |
| db.session.add() / .commit()        | obj.save()  or  Model.objects.create()|
| Model.query.all()                   | Model.objects.all()                  |
| Model.query.filter_by(x=y)          | Model.objects.filter(x=y)            |
| Model.query.get_or_404(id)          | get_object_or_404(Model, pk=id)      |
──────────────────────────────────────────────────────────────────────────────

.to_dict() methods are REMOVED from models.
Django REST Framework serializers (serializers.py) handle that job cleanly.
"""

from django.db import models
from django.utils import timezone


# ── Professeur ────────────────────────────────────────────────────────────────

class Professeur(models.Model):
    """
    SQLAlchemy version had:
        id            = db.Column(db.String(30), primary_key=True)
        specialites   = db.Column(db.Text)   # stored as "spec1; spec2; spec3"
        disponibilites= db.Column(db.Text)   # stored as "2025-06-09 matin; ..."

    Django version keeps the same storage format (semicolon-separated strings)
    so your existing csp_scheduler.py and nlp_matcher.py work without changes.
    """

    # Primary key is a string ID (e.g. "PROF001") — not auto-increment
    # SQLAlchemy: db.Column(db.String(30), primary_key=True)
    id = models.CharField(max_length=30, primary_key=True)

    nom    = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)

    # SQLAlchemy: db.Column(db.String(50), nullable=False)
    # Django:     blank=False is the default, so no extra keyword needed
    domaine = models.CharField(max_length=50)

    # SQLAlchemy: db.Column(db.Text)  — nullable by default
    # Django:     blank=True allows empty string, null=True allows NULL in DB
    specialites    = models.TextField(blank=True, default="")
    grade          = models.CharField(max_length=50, blank=True, default="")
    disponibilites = models.TextField(blank=True, default="")

    # ── Helper methods (kept from SQLAlchemy version) ──────────────────────────
    # Used internally by csp_scheduler.py — not exposed via API directly.
    def specialites_list(self):
        if not self.specialites:
            return []
        return [s.strip() for s in self.specialites.split(";") if s.strip()]

    def disponibilites_list(self):
        if not self.disponibilites:
            return []
        return [d.strip() for d in self.disponibilites.split(";") if d.strip()]

    def __str__(self):
        # Django admin and shell use this for display
        return f"{self.prenom} {self.nom} ({self.domaine})"

    class Meta:
        # SQLAlchemy: __tablename__ = "professeurs"
        db_table  = "professeurs"
        ordering  = ["nom", "prenom"]   # default sort in querysets


# ── Etudiant ──────────────────────────────────────────────────────────────────

class Etudiant(models.Model):
    """
    SQLAlchemy version had a db.relationship("Professeur") for the encadrant.
    Django handles relationships through ForeignKey — no separate relationship()
    call needed. Django automatically creates a reverse accessor on Professeur:
        prof.etudiants_encadres.all()   ← same name we set with related_name
    """

    id       = models.CharField(max_length=20, primary_key=True)
    nom      = models.CharField(max_length=80)
    prenom   = models.CharField(max_length=80)
    domaine  = models.CharField(max_length=50)

    # TextField for long thesis subjects
    sujet    = models.TextField()

    # ForeignKey replaces:
    #   encadrant_id = db.Column(db.String(30), db.ForeignKey("professeurs.id"))
    #   encadrant    = db.relationship("Professeur", ...)
    #
    # on_delete=models.PROTECT → prevents deleting a prof who still supervises students
    # related_name  → lets you do  professeur.etudiants_encadres.all()
    encadrant = models.ForeignKey(
        Professeur,
        on_delete=models.PROTECT,
        related_name="etudiants_encadres",
        db_column="encadrant_id",   # keeps the same column name as SQLAlchemy version
    )

    annee = models.CharField(max_length=10, blank=True, default="")

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.sujet[:50]}"

    class Meta:
        db_table = "etudiants"
        ordering = ["domaine", "nom"]


# ── Creneau ───────────────────────────────────────────────────────────────────

class Creneau(models.Model):
    """
    Represents a time slot in a room on a given date.
    e.g.  id="CR0001", date="2025-06-09", slot="08:00-10:00", salle="Salle A"
    """

    id       = models.CharField(max_length=20, primary_key=True)
    date     = models.CharField(max_length=12)   # stored as "YYYY-MM-DD" string
    slot     = models.CharField(max_length=20)   # "08:00-10:00" etc.
    salle    = models.CharField(max_length=50, blank=True, default="")
    capacite = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.date} {self.slot} — {self.salle}"

    class Meta:
        db_table = "creneaux"
        ordering = ["date", "slot"]


# ── Affectation ───────────────────────────────────────────────────────────────

class Affectation(models.Model):
    """
    The core output of the CSP scheduler.
    Links one student to (examinateur + président + créneau).

    SQLAlchemy had THREE separate db.relationship() calls for the three prof FKs.
    Django handles all three with ForeignKey — each needs a unique related_name
    to avoid clashes on the Professeur model.
    """

    # Auto-increment integer PK (same as SQLAlchemy autoincrement=True)
    # Django adds this automatically — no need to declare it explicitly,
    # but we keep it here for clarity.
    # id = models.BigAutoField(primary_key=True)  ← added automatically by Django

    etudiant = models.OneToOneField(
        Etudiant,
        on_delete=models.CASCADE,
        related_name="affectation",
        db_column="etudiant_id",
        # OneToOne because each student has exactly one jury assignment
    )

    examinateur = models.ForeignKey(
        Professeur,
        on_delete=models.SET_NULL,
        null=True,
        related_name="affectations_examinateur",
        db_column="examinateur_id",
    )

    president = models.ForeignKey(
        Professeur,
        on_delete=models.SET_NULL,
        null=True,
        related_name="affectations_president",
        db_column="president_id",
    )

    creneau = models.ForeignKey(
        Creneau,
        on_delete=models.SET_NULL,
        null=True,
        related_name="affectations",
        db_column="creneau_id",
    )

    # NLP similarity scores stored by the scheduler
    score_exam = models.FloatField(default=0.0)
    score_pres = models.FloatField(default=0.0)

    # SQLAlchemy: db.Column(db.DateTime, default=datetime.utcnow)
    # Django:     auto_now_add=True sets the value once at creation time
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        etu = str(self.etudiant) if self.etudiant else "?"
        return f"Affectation({etu})"

    class Meta:
        db_table = "affectations"
        ordering = ["creneau__date", "creneau__slot"]