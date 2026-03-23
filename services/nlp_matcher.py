"""
services/nlp_matcher.py

NLP similarity engine — matches student thesis subjects to professor specialities.

Flask vs Django changes
──────────────────────────────────────────────────────────────────────────────
This file has ZERO logic changes from the Flask version.
sentence-transformers, numpy, and scikit-learn have no Flask dependency.

Structural change only:
    Flask location:  app/services/nlp_matcher.py
    Django location: services/nlp_matcher.py   (project root level)

Import in csp_scheduler.py:
    from services.nlp_matcher import matcher as nlp_matcher
──────────────────────────────────────────────────────────────────────────────

What this service does
──────────────────────
Given N student subjects and M professors, compute an (N × M) similarity
matrix where entry [i][j] is the semantic similarity between:
    - student i's thesis subject  (sujet)
    - professor j's specialities  (specialites, semicolon-separated)

Similarity is computed using:
    1. sentence-transformers  →  encode text to dense embedding vectors
    2. cosine_similarity      →  measure angle between embedding vectors
                                  (1.0 = identical meaning, 0.0 = unrelated)

The model is loaded ONCE at module import time (singleton pattern) and reused
across all requests — loading a transformer model takes ~5 seconds so we
absolutely do not want to reload it on every POST /api/scheduler/run/.

In Django this works naturally because:
    - Django's dev server is a single process
    - In production (gunicorn), each worker loads the module once
    - The `matcher` singleton at the bottom of this file is shared within a worker
"""

import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("services")


class NLPMatcher:
    """
    Singleton NLP engine.

    Lazy-loads the sentence-transformer model on first use.
    This means the ~5s model load happens on the first POST /api/scheduler/run/
    request, not at Django startup — keeps startup fast.

    Usage (from csp_scheduler.py):
        from services.nlp_matcher import matcher
        score_matrix = matcher.batch_scores(sujets, professeurs)
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Parameters
        ──────────
        model_name : HuggingFace model identifier.
            "paraphrase-multilingual-MiniLM-L12-v2" is a good default:
                - Multilingual  → handles French subjects and specialities
                - MiniLM        → fast inference, small memory footprint
                - 384-dim vectors → good balance of quality and speed
        """
        self.model_name = model_name
        self._model     = None   # lazy-loaded on first call to _get_model()

    # ── Model loading ─────────────────────────────────────────────────────────

    def _get_model(self):
        """
        Lazy loader — loads the transformer model on first call.
        Subsequent calls return the cached model immediately.

        Thread safety: Django's dev server is single-threaded.
        In production with gunicorn --workers N, each worker loads its own
        model copy. This is acceptable — don't use threading model with this.
        """
        if self._model is None:
            logger.info("Chargement du modèle NLP : %s …", self.model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("Modèle NLP chargé.")
        return self._model

    # ── Text preparation ──────────────────────────────────────────────────────

    def _prof_text(self, prof: dict) -> str:
        """
        Builds a single text string representing a professor's expertise.
        Combines domaine and specialites so the embedding captures both
        the broad field and the specific topics.

        Example output:
            "Informatique intelligence artificielle; apprentissage automatique"
        """
        domaine     = str(prof.get("domaine", ""))
        specialites = prof.get("specialites", "")

        # specialites can be a list (already parsed) or a semicolon string
        if isinstance(specialites, list):
            specialites_str = "; ".join(specialites)
        else:
            specialites_str = str(specialites)

        return f"{domaine} {specialites_str}".strip()

    # ── Batch scoring ─────────────────────────────────────────────────────────

    def batch_scores(self, sujets: list, professeurs: list) -> np.ndarray:
        """
        Computes the full (N_students × N_professors) similarity matrix.

        This is called ONCE per scheduler run with ALL students and professors —
        not once per student. Batch encoding is ~10x faster than individual calls.

        Parameters
        ──────────
        sujets      : list of thesis subject strings (one per student)
        professeurs : list of professor dicts (with domaine + specialites)

        Returns
        ───────
        numpy array of shape (len(sujets), len(professeurs))
        Values are cosine similarities in range [0.0, 1.0].

        Example
        ───────
        sujets      = ["Détection d'anomalies par deep learning", ...]
        professeurs = [{"domaine": "Informatique", "specialites": ["deep learning"]}, ...]
        matrix[0][0] → 0.87  (high match)
        matrix[0][5] → 0.12  (low match — different field)
        """
        if not sujets or not professeurs:
            return np.zeros((len(sujets), len(professeurs)))

        model = self._get_model()

        # Build text representations
        prof_texts = [self._prof_text(p) for p in professeurs]

        # Encode all texts in one batch (GPU-accelerated if available)
        # show_progress_bar=False keeps server logs clean
        logger.info(
            "Encodage NLP : %d sujets × %d profs …", len(sujets), len(professeurs)
        )
        sujet_embeddings = model.encode(sujets,      show_progress_bar=False)
        prof_embeddings  = model.encode(prof_texts,  show_progress_bar=False)

        # Cosine similarity matrix: shape (N_students, N_profs)
        # sklearn's cosine_similarity handles normalisation internally
        scores = cosine_similarity(sujet_embeddings, prof_embeddings)

        logger.info(
            "NLP terminé : moy=%.3f max=%.3f min=%.3f",
            scores.mean(), scores.max(), scores.min(),
        )
        return scores

    # ── Single score (utility, not used by CSP engine) ────────────────────────

    def score(self, sujet: str, prof: dict) -> float:
        """
        Computes similarity for a single (subject, professor) pair.
        Useful for testing and manual inspection in the Django shell:

            python manage.py shell
            >>> from services.nlp_matcher import matcher
            >>> matcher.score("Détection d'anomalies", {"domaine": "Informatique", "specialites": ["ML"]})
            0.82
        """
        matrix = self.batch_scores([sujet], [prof])
        return float(matrix[0][0])


# ── Module-level singleton ────────────────────────────────────────────────────
# Instantiated once when the module is first imported.
# All views and services share this single instance.
#
# To use a different model, change the model_name here:
#   "paraphrase-multilingual-MiniLM-L12-v2"  ← fast, multilingual (default)
#   "paraphrase-multilingual-mpnet-base-v2"  ← slower, higher quality
#   "distiluse-base-multilingual-cased-v2"   ← alternative multilingual

matcher = NLPMatcher(model_name="paraphrase-multilingual-MiniLM-L12-v2")