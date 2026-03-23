"""
services/file_parser.py

Excel / CSV parsing service.

Flask vs Django changes
──────────────────────────────────────────────────────────────────────────────
This file is almost identical to the Flask version.
The parsing logic (pandas, openpyxl) has zero Flask dependency — it just
reads files from disk and returns plain Python dicts.

The only change: this file now lives at  services/file_parser.py
(at the project root level, not inside a Flask app package).
It is imported in views.py as:
    from services.file_parser import parse_excel_file, generate_default_creneaux

Make sure services/ has an __init__.py so Python treats it as a package.
──────────────────────────────────────────────────────────────────────────────

What this service does
──────────────────────
Reads an uploaded Excel (.xlsx / .xls) or CSV file and returns four lists:
    etudiants   → list of dicts  (one per student row)
    professeurs → list of dicts  (one per professor row)
    creneaux    → list of dicts  (one per time slot row)
    errors      → list of str    (validation error messages)

The dicts are consumed by UploadView in views.py which maps them to
Django model instances using update_or_create().
"""

import pandas as pd
import os
from typing import Tuple


# ── Required column sets (unchanged from Flask version) ───────────────────────
# These are checked after lowercasing all column names so casing in the
# Excel file doesn't matter ("Nom", "NOM", "nom" all work).

REQUIRED_ETUDIANTS   = {"etudiant_id", "nom", "prenom", "domaine", "sujet", "encadrant_id"}
REQUIRED_PROFESSEURS = {"prof_id", "nom", "prenom", "domaine", "specialites", "disponibilites"}
REQUIRED_CRENEAUX    = {"creneau_id", "date", "slot", "salle"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_file(path: str, sheet: str = None) -> pd.DataFrame:
    """
    Reads a sheet from an Excel file or a CSV file into a DataFrame.
    Supports .xlsx, .xls, and .csv.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path, sheet_name=sheet)
    elif ext == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    raise ValueError(f"Format non supporté : {ext}")


def _validate_columns(df: pd.DataFrame, required: set, sheet_name: str) -> list:
    """
    Checks that all required columns exist in the DataFrame.
    Comparison is case-insensitive (columns are already lowercased by _clean_df).
    Returns a list of error strings — empty list means OK.
    """
    cols    = {c.strip().lower() for c in df.columns}
    missing = required - cols
    if missing:
        return [f"Feuille '{sheet_name}' : colonnes manquantes → {', '.join(sorted(missing))}"]
    return []


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalises a raw DataFrame:
      - Lowercases and strips all column names
      - Drops completely empty rows
      - Fills NaN with empty string
      - Strips whitespace from all string cells
    This ensures consistent dict keys regardless of Excel formatting.
    """
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.dropna(how="all")
    df = df.fillna("")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_excel_file(path: str) -> Tuple[list, list, list, list]:
    """
    Entry point called by UploadView.

    Accepts a path to a saved Excel or CSV file.
    Returns (etudiants, professeurs, creneaux, errors).

    Excel files must have three sheets (case-insensitive names):
        "Etudiants"   or "Étudiants"
        "Professeurs"
        "Creneaux"    or "Créneaux"

    CSV files must contain student columns only (single-sheet format).

    On validation error: errors list is non-empty, other lists may be empty.
    The caller (UploadView) returns HTTP 422 if errors is non-empty.
    """
    errors      = []
    etudiants   = []
    professeurs = []
    creneaux    = []

    ext = os.path.splitext(path)[1].lower()

    if ext in [".xlsx", ".xls"]:
        xl = pd.ExcelFile(path)

        # Build a lowercase→original sheet name map for case-insensitive lookup
        sheet_names_lower = {s.lower(): s for s in xl.sheet_names}

        # ── Étudiants sheet ───────────────────────────────────────────────────
        etu_sheet = (
            sheet_names_lower.get("etudiants")
            or sheet_names_lower.get("étudiants")
            or xl.sheet_names[0]   # fallback to first sheet
        )
        df_etu = _clean_df(pd.read_excel(path, sheet_name=etu_sheet))
        errs   = _validate_columns(df_etu, REQUIRED_ETUDIANTS, "Etudiants")
        errors.extend(errs)
        if not errs:
            etudiants = df_etu.to_dict(orient="records")

        # ── Professeurs sheet ─────────────────────────────────────────────────
        prof_sheet = sheet_names_lower.get("professeurs") or (
            xl.sheet_names[1] if len(xl.sheet_names) > 1 else None
        )
        if prof_sheet:
            df_prof = _clean_df(pd.read_excel(path, sheet_name=prof_sheet))

            # Rename prof_id → id for consistency with the model's PK field name
            if "prof_id" in df_prof.columns:
                df_prof = df_prof.rename(columns={"prof_id": "id"})

            errs = _validate_columns(
                df_prof,
                {"id", "nom", "prenom", "domaine", "specialites", "disponibilites"},
                "Professeurs",
            )
            errors.extend(errs)
            if not errs:
                professeurs = df_prof.to_dict(orient="records")

        # ── Créneaux sheet ────────────────────────────────────────────────────
        cr_sheet = (
            sheet_names_lower.get("creneaux")
            or sheet_names_lower.get("créneaux")
            or (xl.sheet_names[2] if len(xl.sheet_names) > 2 else None)
        )
        if cr_sheet:
            df_cr = _clean_df(pd.read_excel(path, sheet_name=cr_sheet))

            # Rename creneau_id → id for consistency
            if "creneau_id" in df_cr.columns:
                df_cr = df_cr.rename(columns={"creneau_id": "id"})

            errs = _validate_columns(df_cr, {"id", "date", "slot", "salle"}, "Creneaux")
            errors.extend(errs)
            if not errs:
                creneaux = df_cr.to_dict(orient="records")

    elif ext == ".csv":
        # CSV files contain students only (single-sheet format)
        df   = _clean_df(pd.read_csv(path, encoding="utf-8-sig"))
        cols = set(df.columns)
        if REQUIRED_ETUDIANTS.issubset(cols):
            etudiants = df.to_dict(orient="records")
        else:
            errors.append("CSV : colonnes étudiants manquantes")

    # ── Final validation ──────────────────────────────────────────────────────
    if not etudiants:
        errors.append("Aucun étudiant trouvé dans le fichier.")
    if not professeurs:
        errors.append("Aucun professeur trouvé — vérifiez la feuille 'Professeurs'.")

    return etudiants, professeurs, creneaux, errors


# ── Default créneau generator ─────────────────────────────────────────────────

def generate_default_creneaux() -> list:
    """
    Called by UploadView when the Excel file has no 'Creneaux' sheet.
    Generates weekday slots for a two-week period (09–20 June 2025).

    Returns a list of dicts compatible with the Creneau model:
        { id, date (YYYY-MM-DD), slot (HH:MM-HH:MM), salle, capacite }

    5 salles × 4 slots × 10 weekdays = 200 créneaux total.
    Each créneau has capacite=1 (one jury per room per slot).
    """
    from datetime import date, timedelta

    creneaux = []
    start    = date(2025, 6, 9)
    cid      = 1
    salles   = ["Salle A", "Salle B", "Salle C", "Amphi 1", "Labo"]
    slots    = ["08:00-10:00", "10:00-12:00", "14:00-16:00", "16:00-18:00"]

    for i in range(14):
        d = start + timedelta(days=i)
        if d.weekday() < 5:   # Monday–Friday only (weekday() 0=Mon, 6=Sun)
            for slot in slots:
                for salle in salles:
                    creneaux.append({
                        "id":       f"CR{cid:04d}",
                        "date":     d.strftime("%Y-%m-%d"),
                        "slot":     slot,
                        "salle":    salle,
                        "capacite": 1,
                    })
                    cid += 1

    return creneaux