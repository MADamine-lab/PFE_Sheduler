"""
services/csp_scheduler.py

CSP (Constraint Satisfaction Problem) jury assignment engine.

Flask vs Django changes
──────────────────────────────────────────────────────────────────────────────
This file has ZERO logic changes from the Flask version.
The CSP algorithm is pure Python — it has no Flask or SQLAlchemy dependency.
It receives plain dicts from views.py and returns plain dicts back.

The only structural change:
    Flask location:  app/services/csp_scheduler.py   (inside Flask package)
    Django location: services/csp_scheduler.py       (at project root level)

Import in views.py:
    from services.csp_scheduler import PFEScheduler
    import services.csp_scheduler as csp_mod

Make sure services/__init__.py exists so Python treats it as a package.
──────────────────────────────────────────────────────────────────────────────

How the CSP engine works (summary)
──────────────────────────────────
1.  NLP pre-pass:  batch_scores() computes a (n_students × n_profs) similarity
    matrix using sentence-transformers in one shot.

2.  Sort students by (domaine, encadrant_id) so students in the same
    speciality are assigned to adjacent time slots — grouping jury members
    together reduces travel between rooms.

3.  For each student, _assign_one() runs a backtracking search:
    a. Build candidate list: professors with NLP score ≥ threshold,
       excluding the supervisor (encadrant).
    b. Progressive threshold relaxation if < 2 candidates found.
    c. Backtrack over (examiner, president) pairs ranked by NLP score (MRV).
    d. For each pair, _find_creneau() finds the least-loaded available slot
       where both professors are free (min-conflicts heuristic).

4.  Results returned as a list of dicts:
        { etudiant_id, examinateur_id, president_id, creneau_id,
          score_exam, score_pres }
    which views.py maps to Affectation model instances.
"""

import numpy as np
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("services")

# Configurable via POST /api/scheduler/run/ body → { "max_jury_per_day": 4 }
# views.py does:  import services.csp_scheduler as csp_mod
#                 csp_mod.MAX_JURY_PER_DAY = max_jury
MAX_JURY_PER_DAY = 4


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_dispo(dispo_str: str) -> set:
    """
    Parses a semicolon-separated availability string into a set of keys.
    e.g. "2025-06-09 matin; 2025-06-10 après-midi"
         → {"2025-06-09 matin", "2025-06-10 après-midi"}

    Empty or missing string → empty set (professor has no availability → never assigned).
    """
    if not dispo_str:
        return set()
    return {d.strip() for d in str(dispo_str).split(";") if d.strip()}


def _creneau_key(cr: dict) -> str:
    """
    Converts a créneau dict to the same format used in professor availability strings.
    e.g.  { date: "2025-06-09", slot: "08:00-10:00" }  →  "2025-06-09 matin"

    This allows direct comparison:
        if _creneau_key(cr) in prof_dispo_set → prof is available for this slot
    """
    slot_map = {
        "08:00-10:00": "matin",
        "10:00-12:00": "matin",
        "14:00-16:00": "après-midi",
        "16:00-18:00": "après-midi",
    }
    period = slot_map.get(str(cr.get("slot", "")), str(cr.get("slot", "")))
    return f"{cr['date']} {period}"


# ── Main engine ───────────────────────────────────────────────────────────────

class PFEScheduler:
    """
    Stateful scheduler — create a new instance for each /run call.
    State is reset automatically because RunSchedulerView instantiates
    a fresh PFEScheduler() on every POST request.

    Internal state tracks:
        _jury_load      : total assignments per professor (for fairness reporting)
        _jury_day_load  : assignments per professor per day (enforces MAX_JURY_PER_DAY)
        _creneau_usage  : professors already assigned to each slot (prevents double-booking)
        _affectations   : successfully resolved assignments
        _unresolved     : students for whom no valid assignment was found
    """

    def __init__(self):
        self._jury_load     = defaultdict(int)
        self._jury_day_load = defaultdict(lambda: defaultdict(int))
        self._creneau_usage = defaultdict(list)
        self._affectations  = []
        self._unresolved    = []
        self.stats          = {}

    # ── Public entry point ────────────────────────────────────────────────────

    def run(
        self,
        etudiants:     list,
        professeurs:   list,
        creneaux:      list,
        nlp_threshold: float = 0.10,
    ) -> dict:
        """
        Main entry point called by RunSchedulerView.

        Parameters
        ──────────
        etudiants   : list of dicts with keys id, nom, prenom, domaine, sujet, encadrant_id
        professeurs : list of dicts with keys id, nom, prenom, domaine, specialites, disponibilites
        creneaux    : list of dicts with keys id, date, slot, salle
        nlp_threshold : minimum NLP similarity score for a professor to be a candidate

        Returns
        ───────
        {
            "affectations": [ { etudiant_id, examinateur_id, president_id,
                                 creneau_id, score_exam, score_pres }, ... ],
            "unresolved":   [ { id, ... }, ... ],  ← students with no valid assignment
            "stats":        { total, resolved, unresolved },
        }
        """
        logger.info(
            "CSP start : %d étudiants | %d profs | %d créneaux | seuil=%.2f",
            len(etudiants), len(professeurs), len(creneaux), nlp_threshold,
        )

        if not etudiants or not professeurs or not creneaux:
            raise ValueError("Données manquantes : étudiants, profs ou créneaux vides")

        # ── Step 1: NLP pre-computation ───────────────────────────────────────
        # batch_scores() encodes all subjects in one pass — much faster than
        # computing each (subject, professor) pair individually.
        # score_matrix shape: (n_etudiants, n_professeurs)
        from services.nlp_matcher import matcher as nlp_matcher

        sujets       = [str(e.get("sujet", "")) for e in etudiants]
        score_matrix = nlp_matcher.batch_scores(sujets, professeurs)
        prof_index   = {p["id"]: i for i, p in enumerate(professeurs)}

        logger.info(
            "NLP scores : moy=%.3f max=%.3f min=%.3f",
            score_matrix.mean(), score_matrix.max(), score_matrix.min(),
        )

        # ── Step 2: Sort students to group by domain ──────────────────────────
        # Students in the same domain tend to have the same jury members,
        # so sorting keeps jury assignments clustered on the same dates.
        etudiants_sorted = sorted(
            etudiants,
            key=lambda e: (str(e.get("domaine", "")), str(e.get("encadrant_id", ""))),
        )

        # ── Step 3: Assign each student via backtracking ──────────────────────
        for etu in etudiants_sorted:
            try:
                etu_idx    = etudiants.index(etu)
                etu_scores = score_matrix[etu_idx]
                result     = self._assign_one(
                    etu, professeurs, creneaux, etu_scores, prof_index, nlp_threshold
                )
                if result:
                    self._affectations.append(result)
                else:
                    logger.warning(
                        "Non résolu : %s | sujet=%s", etu["id"], etu.get("sujet", "")[:40]
                    )
                    self._unresolved.append(etu)
            except Exception as exc:
                logger.error("Erreur pour étudiant %s : %s", etu.get("id"), exc)
                self._unresolved.append(etu)

        self.stats = {
            "total":      len(etudiants),
            "resolved":   len(self._affectations),
            "unresolved": len(self._unresolved),
        }
        logger.info(
            "CSP terminé : %d résolus / %d | %d non-résolus",
            self.stats["resolved"], self.stats["total"], self.stats["unresolved"],
        )
        return {
            "affectations": self._affectations,
            "unresolved":   self._unresolved,
            "stats":        self.stats,
        }

    # ── Single student assignment ─────────────────────────────────────────────

    def _assign_one(
        self,
        etu:         dict,
        professeurs: list,
        creneaux:    list,
        etu_scores:  np.ndarray,
        prof_index:  dict,
        threshold:   float,
    ) -> Optional[dict]:
        """
        Assigns one student to (examinateur, président, créneau) using backtracking.

        Candidate filtering
        ───────────────────
        1. Remove encadrant from candidates (a supervisor cannot be on their own jury)
        2. Keep only professors with NLP score ≥ threshold
        3. If fewer than 2 candidates: relax threshold progressively (÷2, then 0)
        4. Sort candidates by NLP score descending (MRV heuristic — try best first)

        Backtracking
        ────────────
        Try all (examiner i, president j) pairs where i ≠ j.
        For each pair, find a common available créneau via _find_creneau().
        Return the first valid assignment found.
        Return None if no valid (pair, créneau) combination exists.
        """
        encadrant_id = str(etu.get("encadrant_id", ""))

        def get_candidates(thr):
            return [
                p for p in professeurs
                if p["id"] != encadrant_id
                and etu_scores[prof_index[p["id"]]] >= thr
            ]

        # Progressive threshold relaxation
        candidates = get_candidates(threshold)
        if len(candidates) < 2:
            candidates = get_candidates(threshold / 2)
        if len(candidates) < 2:
            candidates = get_candidates(0.0)
        if len(candidates) < 2:
            candidates = [p for p in professeurs if p["id"] != encadrant_id]

        if len(candidates) < 2:
            logger.warning("Pas assez de candidats pour %s", etu["id"])
            return None

        # Sort by NLP score descending — best match tried first
        candidates.sort(key=lambda p: -float(etu_scores[prof_index[p["id"]]]))

        # Backtracking loop
        for i, exam in enumerate(candidates):
            for j, pres in enumerate(candidates):
                if i == j:
                    continue

                creneau = self._find_creneau(exam, pres, creneaux)
                if creneau is None:
                    continue

                # Valid assignment found — update state and return
                date = creneau["date"]
                self._jury_load[exam["id"]] += 1
                self._jury_load[pres["id"]] += 1
                self._jury_day_load[exam["id"]][date] += 1
                self._jury_day_load[pres["id"]][date] += 1
                self._creneau_usage[creneau["id"]].append(exam["id"])
                self._creneau_usage[creneau["id"]].append(pres["id"])

                return {
                    "etudiant_id":    etu["id"],
                    "examinateur_id": exam["id"],
                    "president_id":   pres["id"],
                    "creneau_id":     creneau["id"],
                    "score_exam":     float(etu_scores[prof_index[exam["id"]]]),
                    "score_pres":     float(etu_scores[prof_index[pres["id"]]]),
                }

        return None   # no valid assignment found after full backtracking

    # ── Common créneau finder ─────────────────────────────────────────────────

    def _find_creneau(
        self,
        exam:     dict,
        pres:     dict,
        creneaux: list,
    ) -> Optional[dict]:
        """
        Finds the best available créneau for (examiner, president) pair.

        Constraints checked
        ───────────────────
        1. Créneau key must be in BOTH professors' availability sets (intersection)
        2. Neither professor is already booked for that créneau
        3. Neither professor has reached MAX_JURY_PER_DAY assignments on that date

        Min-conflicts heuristic
        ───────────────────────
        Among all valid créneaux, prefer the one with the fewest existing
        bookings (least-loaded slot first). This distributes assignments
        evenly across the schedule rather than packing early slots.
        """
        exam_dispo = _parse_dispo(exam.get("disponibilites", ""))
        pres_dispo = _parse_dispo(pres.get("disponibilites", ""))
        common     = exam_dispo & pres_dispo

        # No common availability → this pair cannot share any créneau
        if not common:
            return None

        valid = []
        for cr in creneaux:
            key = _creneau_key(cr)
            if key not in common:
                continue

            # Check if either prof is already booked for this créneau
            usage = self._creneau_usage.get(cr["id"], [])
            if exam["id"] in usage or pres["id"] in usage:
                continue

            # Enforce daily jury limit
            date = cr["date"]
            if self._jury_day_load[exam["id"]][date] >= MAX_JURY_PER_DAY:
                continue
            if self._jury_day_load[pres["id"]][date] >= MAX_JURY_PER_DAY:
                continue

            # Score this créneau by current load (lower = preferred)
            valid.append((len(usage), cr))

        if not valid:
            return None

        # Return least-loaded créneau (min-conflicts)
        valid.sort(key=lambda x: x[0])
        return valid[0][1]