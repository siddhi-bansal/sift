"""Clustering PAIN/DISCUSSION items: embeddings (Gemini) or TF-IDF fallback."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def _tfidf_vectors(texts: list[str], max_features: int = 500) -> np.ndarray:
    vec = TfidfVectorizer(max_features=max_features, stop_words="english", ngram_range=(1, 2))
    return vec.fit_transform(texts).toarray()


def cluster_with_tfidf(
    items: list[dict[str, Any]],
    text_key: str = "text",
    n_clusters: int | None = None,
    min_cluster_size: int = 2,
) -> list[list[int]]:
    """
    Cluster items by TF-IDF + KMeans. Returns list of clusters, each a list of item indices.
    """
    texts = [(item.get("title") or "") + " " + (item.get(text_key) or "") for item in items]
    if not texts or all(not t.strip() for t in texts):
        return [[i] for i in range(len(items))]
    X = _tfidf_vectors(texts)
    n = min(max(1, len(items) // 3), len(items), 15)
    n_clusters = n_clusters or n
    if n_clusters >= len(items):
        return [[i] for i in range(len(items))]
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    clusters: list[list[int]] = [[] for _ in range(n_clusters)]
    for i, lb in enumerate(labels):
        clusters[lb].append(i)
    # Drop tiny clusters into nearest by centroid
    kept: list[list[int]] = [c for c in clusters if len(c) >= min_cluster_size]
    orphans = [i for c in clusters if len(c) < min_cluster_size for i in c]
    if orphans and kept:
        centroids = [np.mean(X[c], axis=0) for c in kept]
        for i in orphans:
            sims = [cosine_similarity(X[i : i + 1], [c])[0, 0] for c in centroids]
            best = int(np.argmax(sims))
            kept[best].append(i)
    elif orphans:
        kept = [orphans]
    return kept


def cluster_with_embeddings(
    items: list[dict[str, Any]],
    embeddings: list[list[float]],
    n_clusters: int | None = None,
    min_cluster_size: int = 2,
) -> list[list[int]]:
    """Cluster by embedding vectors using KMeans (HDBSCAN needs extra dep)."""
    X = np.array(embeddings, dtype=float)
    if X.shape[0] < 2:
        return [[i] for i in range(len(items))]
    n = min(max(1, len(items) // 3), len(items), 15)
    n_clusters = n_clusters or n
    if n_clusters >= len(items):
        return [[i] for i in range(len(items))]
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    clusters: list[list[int]] = [[] for _ in range(n_clusters)]
    for i, lb in enumerate(labels):
        clusters[lb].append(i)
    kept = [c for c in clusters if len(c) >= min_cluster_size]
    orphans = [i for c in clusters if len(c) < min_cluster_size for i in c]
    if orphans and kept:
        centroids = [np.mean(X[c], axis=0) for c in kept]
        for i in orphans:
            sims = [cosine_similarity(X[i : i + 1], [c])[0, 0] for c in centroids]
            best = int(np.argmax(sims))
            kept[best].append(i)
    elif orphans:
        kept = [orphans]
    return kept


def top_terms_tfidf(texts: list[str], k: int = 5, max_features: int = 200) -> list[str]:
    """Extract top terms for a cluster via TF-IDF on its texts."""
    if not texts:
        return []
    vec = TfidfVectorizer(max_features=max_features, stop_words="english", ngram_range=(1, 2))
    m = vec.fit_transform(texts)
    scores = np.asarray(m.sum(axis=0)).ravel()
    order = np.argsort(-scores)[:k]
    names = vec.get_feature_names_out()
    return [names[i] for i in order if i < len(names)]
