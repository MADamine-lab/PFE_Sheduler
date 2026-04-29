"""
scheduler/serializers.py

Django REST Framework Serializers.

This file has NO Flask equivalent — it is a DRF concept.
It replaces every  .to_dict()  method you had scattered across models.py.

Why serializers are better than .to_dict()
──────────────────────────────────────────────────────────────────────────────
  .to_dict()  (Flask)          |  Serializer  (DRF)
  ─────────────────────────────|────────────────────────────────────────────
  Only serializes (→ JSON)     |  Serializes AND deserializes (→ validated Python)
  No validation                |  Built-in field validation + custom rules
  Manual nested objects        |  Nested serializers declared once, reused everywhere
  Duplicated across models     |  Single source of truth, imported in any view
  No write support             |  Handles POST/PUT bodies automatically
──────────────────────────────────────────────────────────────────────────────

How a serializer works (mental model)
──────────────────────────────────────
  READ  (GET):   Model instance  →  serializer.data  →  Response(serializer.data)
  WRITE (POST):  request.data    →  serializer.is_valid()  →  serializer.save()

In views.py you will do:
    serializer = AffectationSerializer(affectation_instance)
    return Response(serializer.data)          # ← replaces return jsonify(aff.to_dict())
"""

from rest_framework import serializers
from .models import Etudiant, Professeur, Creneau, Affectation


# ── Professeur ────────────────────────────────────────────────────────────────

class ProfesseurSerializer(serializers.ModelSerializer):
    """
    Replaces  Professeur.to_dict()  which returned:
        { id, nom, prenom, domaine, specialites (list), grade, disponibilites (list) }

    ModelSerializer automatically maps model fields to serializer fields.
    We only need to declare fields that require special handling.
    """

    # The model stores specialites as "spec1; spec2" (plain string).
    # We expose it as a proper list to React — same as .specialites_list() did.
    # SerializerMethodField → calls  get_<field_name>(self, obj)
    specialites    = serializers.SerializerMethodField()
    disponibilites = serializers.SerializerMethodField()

    class Meta:
        model  = Professeur
        # List every field React will receive.
        # Equivalent to the keys in your old .to_dict() return dict.
        fields = ["id", "nom", "prenom", "domaine", "specialites", "grade", "disponibilites", "email", "telephone"]

    def get_specialites(self, obj):
        # obj is a Professeur instance — same logic as .specialites_list()
        return obj.specialites_list()

    def get_disponibilites(self, obj):
        return obj.disponibilites_list()


class ProfesseurWriteSerializer(serializers.ModelSerializer):
    """
    Used for POST/PUT — accepts specialites and disponibilites as plain strings
    (semicolon-separated) which is how the Excel parser produces them.
    This keeps the write format consistent with file_parser.py output.
    """

    def to_internal_value(self, data):
        # Normalize list inputs into the string format expected by the model
        if isinstance(data, dict):
            data = data.copy()
            for key in ("specialites", "disponibilites"):
                value = data.get(key)
                if isinstance(value, list):
                    data[key] = "; ".join(
                        [str(item).strip() for item in value if str(item).strip()]
                    )
        return super().to_internal_value(data)

    class Meta:
        model  = Professeur
        fields = ["id", "nom", "prenom", "domaine", "specialites", "grade", "disponibilites", "email", "telephone"]


# ── Etudiant ──────────────────────────────────────────────────────────────────

class EtudiantSerializer(serializers.ModelSerializer):
    """
    Replaces  Etudiant.to_dict()  which returned:
        { id, nom, prenom, domaine, sujet, encadrant_id, encadrant_nom, annee }

    encadrant_nom was a computed string — we reproduce it with SerializerMethodField.
    encadrant_id  is a plain FK value — DRF exposes it automatically as a CharField
    when we use  source="encadrant_id".
    """

    # Expose the FK value directly (not the full nested object)
    # source="encadrant_id" reads the raw DB column value (string like "PROF001")
    encadrant_id = serializers.CharField(read_only=True)

    # Computed field — same as  f"{enc.prenom} {enc.nom}"  in .to_dict()
    encadrant_nom = serializers.SerializerMethodField()

    class Meta:
        model  = Etudiant
        fields = ["id", "nom", "prenom", "domaine", "sujet", "encadrant_id", "encadrant_nom", "annee", "email", "telephone"]

    def get_encadrant_nom(self, obj):
        # obj.encadrant is the related Professeur instance (Django loads it automatically)
        if obj.encadrant:
            return f"{obj.encadrant.prenom} {obj.encadrant.nom}"
        return ""


class EtudiantUpdateSerializer(serializers.ModelSerializer):
    """
    Used for PUT /api/etudiant/<id>/ and PUT /api/me/etudiant/
    Allows updating student profile fields:
    - sujet (subject)
    - email
    - telephone
    - encadrant_id (supervisor - now writable for students)
    """

    # Accept encadrant_id on write (FK to Professeur)
    encadrant_id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = Etudiant
        fields = ["sujet", "email", "telephone", "encadrant_id"]

    def validate_encadrant_id(self, value):
        """Validate that the encadrant exists"""
        if value and value.strip():
            # Check if professor with this ID exists
            if not Professeur.objects.filter(id__iexact=value.strip()).exists():
                raise serializers.ValidationError("Encadrant introuvable")
        return value.strip() if value else None

    def save(self, **kwargs):
        """Handle encadrant FK assignment"""
        encadrant_id = self.validated_data.pop("encadrant_id", None)
        instance = super().save(**kwargs)
        
        if encadrant_id:
            try:
                professeur = Professeur.objects.get(id__iexact=encadrant_id)
                instance.encadrant = professeur
                instance.save()
            except Professeur.DoesNotExist:
                pass
        
        return instance


# ── Creneau ───────────────────────────────────────────────────────────────────

class CreneauSerializer(serializers.ModelSerializer):
    """
    Replaces  Creneau.to_dict()
    All fields are plain values — no special handling needed.
    ModelSerializer maps them 1-to-1 from the model.
    """

    class Meta:
        model  = Creneau
        fields = ["id", "date", "slot", "salle", "capacite"]


# ── Affectation ───────────────────────────────────────────────────────────────

class AffectationSerializer(serializers.ModelSerializer):
    """
    Replaces  Affectation.to_dict()  which returned a deeply nested dict:
        {
            id, score_exam, score_pres,
            etudiant:     { ...EtudiantSerializer fields... },
            examinateur:  { ...ProfesseurSerializer fields... },
            president:    { ...ProfesseurSerializer fields... },
            encadrant:    { ...ProfesseurSerializer fields... },
            creneau:      { ...CreneauSerializer fields... },
        }

    Nesting serializers here replaces the manual  enc.to_dict()  calls.
    read_only=True on nested serializers means they are output-only —
    we use separate write logic (AffectationUpdateSerializer) for PUT requests.
    """

    etudiant    = EtudiantSerializer(read_only=True)
    examinateur = ProfesseurSerializer(read_only=True)
    president   = ProfesseurSerializer(read_only=True)
    creneau     = CreneauSerializer(read_only=True)

    # encadrant lives on the etudiant — we expose it at the top level
    # so React doesn't have to dig into affectation.etudiant.encadrant
    encadrant = serializers.SerializerMethodField()

    class Meta:
        model  = Affectation
        fields = [
            "id",
            "etudiant",
            "examinateur",
            "president",
            "encadrant",
            "creneau",
            "score_exam",
            "score_pres",
            "created_at",
        ]

    def get_encadrant(self, obj):
        # Navigate:  affectation → etudiant → encadrant (Professeur)
        if obj.etudiant and obj.etudiant.encadrant:
            return ProfesseurSerializer(obj.etudiant.encadrant).data
        return {}


class AffectationUpdateSerializer(serializers.ModelSerializer):
    """
    Used exclusively for PUT /api/scheduler/affectations/<id>/

    Replaces the manual validation in Flask's  update_affectation()  view:
        if new_exam == enc: return error
        if new_exam == new_pres: return error

    In DRF, validation lives in the serializer — the view stays clean.
    We accept only the three writable FK ids, not the full nested objects.
    """

    # Accept bare IDs on write (e.g. "PROF003") — Django resolves the FK
    examinateur_id = serializers.CharField(required=False)
    president_id   = serializers.CharField(required=False)
    creneau_id     = serializers.CharField(required=False)

    class Meta:
        model  = Affectation
        fields = ["examinateur_id", "president_id", "creneau_id"]

    def validate(self, data):
        """
        Cross-field validation — replaces the if/return blocks in Flask's view.
        DRF calls this automatically before .save().
        Raises serializers.ValidationError → DRF returns HTTP 400 automatically.
        """
        instance      = self.instance           # the existing Affectation row
        encadrant_id  = instance.etudiant.encadrant_id if instance.etudiant else None

        exam_id = data.get("examinateur_id", instance.examinateur_id)
        pres_id = data.get("president_id",   instance.president_id)

        if exam_id and exam_id == encadrant_id:
            raise serializers.ValidationError(
                {"examinateur_id": "L'examinateur ne peut pas être l'encadrant."}
            )
        if pres_id and pres_id == encadrant_id:
            raise serializers.ValidationError(
                {"president_id": "Le président ne peut pas être l'encadrant."}
            )
        if exam_id and pres_id and exam_id == pres_id:
            raise serializers.ValidationError(
                {"president_id": "Le président ne peut pas être l'examinateur."}
            )
        return data


# ── Upload response (not a model serializer) ──────────────────────────────────

class UploadSummarySerializer(serializers.Serializer):
    """
    Shapes the response body of  POST /api/upload/

    Flask returned:
        jsonify({ "message": ..., "warnings": [...], "summary": { etudiants, ... } })

    DRF equivalent — a plain Serializer (not ModelSerializer) for non-model data.
    React can rely on this shape being consistent and validated.
    """

    message  = serializers.CharField()
    warnings = serializers.ListField(child=serializers.CharField(), default=list)
    summary  = serializers.DictField()


# ── Scheduler run response ────────────────────────────────────────────────────

class SchedulerResultSerializer(serializers.Serializer):
    """
    Shapes the response body of  POST /api/scheduler/run/

    Flask returned:
        jsonify({ "message": ..., "stats": {...}, "unresolved": [...] })
    """

    message    = serializers.CharField()
    stats      = serializers.DictField()
    unresolved = serializers.ListField(child=serializers.CharField(), default=list)


# ── Dashboard stats (not a model serializer) ──────────────────────────────────

class DashboardSerializer(serializers.Serializer):
    """
    Shapes the response of  GET /api/stats/dashboard/

    Flask returned a raw jsonify() dict — here we make the shape explicit
    so React always gets consistent field names even if the DB is empty.
    """

    counts       = serializers.DictField()
    by_domain    = serializers.ListField(child=serializers.DictField())
    jury_load    = serializers.ListField(child=serializers.DictField())
    by_date      = serializers.ListField(child=serializers.DictField())
    avg_nlp_scores = serializers.DictField()