"""Hubness diagnostics for a small semantic-retrieval corpus.

Encodes the fixed corpus in ``corpus.json`` with a sentence-embedding model,
then measures the neighbour structure of the resulting space: k-occurrence
counts, their skewness, reciprocal-neighbour rate, rank-1/rank-2 margins, and
what a Cross-domain Similarity Local Scaling (CSLS) correction changes.

Everything the article shows comes from the JSON this writes. Nothing is
hand-tuned after the fact.

Usage:
    python experiment.py [--out ../../src/data/embedding-hubness/hubness.json]
"""

from __future__ import annotations

import argparse
import json
import platform
import random
from pathlib import Path

import numpy as np

SEED = 0
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# k values reported for the document-side neighbour statistics.
K_VALUES = (1, 3, 5, 10)
# Neighbourhood size used both for the retrieval cut-off and for the local
# scaling term in CSLS. Kept identical so the two are directly comparable.
K_RETRIEVAL = 5
K_CSLS = 10

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "src" / "data" / "embedding-hubness" / "hubness.json"


# --------------------------------------------------------------------------
# Similarity, neighbourhoods, hubness
# --------------------------------------------------------------------------


def l2_normalize(x: np.ndarray) -> np.ndarray:
    """Project rows onto the unit sphere so the dot product is the cosine."""
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(norms, 1e-12)


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity between two sets of L2-normalized rows."""
    return l2_normalize(a) @ l2_normalize(b).T


def top_k(sim: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k highest scores per row, highest first."""
    part = np.argpartition(-sim, kth=k - 1, axis=1)[:, :k]
    order = np.take_along_axis(-sim, part, axis=1).argsort(axis=1, kind="stable")
    return np.take_along_axis(part, order, axis=1)


def knn_within(sim: np.ndarray, k: int) -> np.ndarray:
    """k nearest neighbours of each row among the other rows of the same set."""
    masked = sim.copy()
    np.fill_diagonal(masked, -np.inf)
    return top_k(masked, k)


def occurrence_counts(neighbours: np.ndarray, n: int) -> np.ndarray:
    """N_k(j): how many rows list j among their k nearest neighbours."""
    return np.bincount(neighbours.reshape(-1), minlength=n)


def skewness(x: np.ndarray) -> float:
    """Fisher-Pearson standardized third moment, the usual hubness statistic."""
    x = x.astype(float)
    centered = x - x.mean()
    denom = centered.std()
    if denom == 0:
        return 0.0
    return float((centered**3).mean() / denom**3)


def reciprocal_rate(neighbours: np.ndarray) -> float:
    """Share of directed k-NN edges i->j whose reverse edge j->i also exists."""
    sets = [set(row.tolist()) for row in neighbours]
    total = mutual = 0
    for i, row in enumerate(neighbours):
        for j in row.tolist():
            total += 1
            if i in sets[j]:
                mutual += 1
    return mutual / total if total else 0.0


def reciprocated_in_degree(neighbours: np.ndarray, n: int) -> np.ndarray:
    """Of the rows that choose j, how many does j choose back.

    Bounded above by k regardless of how popular j is, which is what makes
    the neighbour relation asymmetric even though cosine is not.
    """
    sets = [set(row.tolist()) for row in neighbours]
    counts = np.zeros(n, dtype=int)
    for i, row in enumerate(neighbours):
        for j in row.tolist():
            if i in sets[j]:
                counts[j] += 1
    return counts


def local_scale(sim_to_reference: np.ndarray, k: int) -> np.ndarray:
    """r_x: mean similarity to the k nearest points of the reference set.

    High r_x means the point sits in a dense region, which is exactly the
    condition under which it tends to be returned for unrelated queries.
    """
    kth = top_k(sim_to_reference, k)
    return np.take_along_axis(sim_to_reference, kth, axis=1).mean(axis=1)


def csls_scores(sim: np.ndarray, r_rows: np.ndarray, r_cols: np.ndarray) -> np.ndarray:
    """CSLS(x, y) = 2 cos(x, y) - r_x - r_y."""
    return 2.0 * sim - r_rows[:, None] - r_cols[None, :]


def cross_topic_in_degree(neighbours: np.ndarray, topics: list[str]) -> np.ndarray:
    """How many of the rows listing j as a neighbour belong to another topic."""
    counts = np.zeros(len(topics), dtype=int)
    for i, row in enumerate(neighbours):
        for j in row.tolist():
            if topics[i] != topics[j]:
                counts[j] += 1
    return counts


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(float)
    b = b.astype(float)
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# --------------------------------------------------------------------------
# Retrieval evaluation
# --------------------------------------------------------------------------


def ranked_ids(scores: np.ndarray, doc_ids: list[str]) -> list[str]:
    return [doc_ids[i] for i in np.argsort(-scores, kind="stable")]


def evaluate(ranking: list[str], relevant: set[str], k: int) -> dict[str, float]:
    hits = [1.0 if d in relevant else 0.0 for d in ranking[:k]]
    reciprocal = 0.0
    for rank, doc in enumerate(ranking, start=1):
        if doc in relevant:
            reciprocal = 1.0 / rank
            break
    dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits))
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return {
        "p_at_1": hits[0],
        "p_at_k": sum(hits) / k,
        "recall_at_k": sum(hits) / len(relevant),
        "mrr": reciprocal,
        "ndcg_at_k": dcg / ideal if ideal else 0.0,
    }


def mean_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: float(np.mean([row[key] for row in rows])) for key in rows[0]}


# --------------------------------------------------------------------------


def round_list(values, digits: int = 4):
    return [round(float(v), digits) for v in values]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus", type=Path, default=HERE / "corpus.json")
    args = parser.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)

    import torch
    from sentence_transformers import SentenceTransformer

    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    docs = corpus["documents"]
    queries = corpus["queries"]
    doc_ids = [d["id"] for d in docs]
    doc_index = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    n_docs = len(docs)

    model = SentenceTransformer(MODEL_NAME, device="cpu")
    model.eval()

    # The title is part of the indexed unit: chunks carry their heading in the
    # setup this corpus imitates. Queries are encoded as-is.
    doc_texts = [f"{d['title']}. {d['text']}" for d in docs]
    query_texts = [q["text"] for q in queries]

    with torch.no_grad():
        doc_emb = l2_normalize(np.asarray(model.encode(doc_texts, batch_size=16)))
        query_emb = l2_normalize(np.asarray(model.encode(query_texts, batch_size=16)))

    # ---- document-side neighbour structure ------------------------------
    topics = [d["topic"] for d in docs]
    dd = cosine_matrix(doc_emb, doc_emb)
    off_diagonal = dd[~np.eye(n_docs, dtype=bool)].reshape(n_docs, n_docs - 1)
    mean_cos = off_diagonal.mean(axis=1)

    # Proximity to the corpus centroid, the standard candidate explanation for
    # why some points become neighbours of everything.
    centroid = doc_emb.mean(axis=0)
    centroid /= np.linalg.norm(centroid)
    cos_centroid = doc_emb @ centroid

    dd_no_self = dd.copy()
    np.fill_diagonal(dd_no_self, -np.inf)
    r_doc = local_scale(dd_no_self, K_CSLS)

    # The same neighbour graph under CSLS. Both scaling terms live in the
    # document space here, so the correction is symmetric and hubness is the
    # only thing it can act on.
    dd_csls = csls_scores(dd, r_doc, r_doc)

    per_k = {}
    for k in K_VALUES:
        neighbours = knn_within(dd, k)
        neighbours_csls = knn_within(dd_csls, k)
        counts = occurrence_counts(neighbours, n_docs)
        counts_csls = occurrence_counts(neighbours_csls, n_docs)
        cross = cross_topic_in_degree(neighbours, topics)
        mutual_in = reciprocated_in_degree(neighbours, n_docs)
        per_k[str(k)] = {
            "counts": {doc_ids[i]: int(counts[i]) for i in range(n_docs)},
            "counts_csls": {doc_ids[i]: int(counts_csls[i]) for i in range(n_docs)},
            "cross_topic": {doc_ids[i]: int(cross[i]) for i in range(n_docs)},
            "reciprocated_in": {doc_ids[i]: int(mutual_in[i]) for i in range(n_docs)},
            "skewness": round(skewness(counts), 3),
            "skewness_csls": round(skewness(counts_csls), 3),
            "max_count": int(counts.max()),
            "max_count_csls": int(counts_csls.max()),
            "mean_count": round(float(counts.mean()), 3),
            "zero_count": int((counts == 0).sum()),
            "zero_count_csls": int((counts_csls == 0).sum()),
            "reciprocal_rate": round(reciprocal_rate(neighbours), 4),
            "reciprocal_rate_csls": round(reciprocal_rate(neighbours_csls), 4),
            # Share of all k-NN slots taken by the five most frequent documents.
            "top5_share": round(float(np.sort(counts)[-5:].sum() / counts.sum()), 4),
            "top5_share_csls": round(float(np.sort(counts_csls)[-5:].sum() / counts_csls.sum()), 4),
            "cross_topic_rate": round(float(cross.sum() / counts.sum()), 4),
            # Does N_k track centroid proximity, or merely average similarity?
            "corr_centroid": round(pearson(counts, cos_centroid), 3),
            "corr_mean_cosine": round(pearson(counts, mean_cos), 3),
        }

    # ---- query-side retrieval, cosine and CSLS --------------------------
    qd = cosine_matrix(query_emb, doc_emb)

    # Local scaling is estimated in the document space for both arguments:
    # r_query is the query's mean similarity to its K_CSLS nearest documents,
    # r_doc the document's mean similarity to its K_CSLS nearest documents,
    # itself excluded. r_query is constant within a query, so it rescales that
    # query's scores without reordering them; the reordering comes from r_doc.
    r_query = local_scale(qd, K_CSLS)
    qd_csls = csls_scores(qd, r_query, r_doc)

    generic_ids = {d["id"] for d in docs if d["topic"] == "generic"}

    query_rows = []
    cosine_eval, csls_eval = [], []
    query_top_counts = np.zeros(n_docs, dtype=int)
    csls_top_counts = np.zeros(n_docs, dtype=int)

    for qi, query in enumerate(queries):
        relevant = set(query["relevant"])
        cos_rank = ranked_ids(qd[qi], doc_ids)
        csls_rank = ranked_ids(qd_csls[qi], doc_ids)
        cos_sorted = np.sort(qd[qi])[::-1]
        csls_sorted = np.sort(qd_csls[qi])[::-1]

        for doc_id in cos_rank[:K_RETRIEVAL]:
            query_top_counts[doc_index[doc_id]] += 1
        for doc_id in csls_rank[:K_RETRIEVAL]:
            csls_top_counts[doc_index[doc_id]] += 1

        cosine_eval.append(evaluate(cos_rank, relevant, K_RETRIEVAL))
        csls_eval.append(evaluate(csls_rank, relevant, K_RETRIEVAL))

        cos_positions = {doc_id: i for i, doc_id in enumerate(cos_rank)}
        query_rows.append(
            {
                "id": query["id"],
                "text": query["text"],
                "style": query.get("style", "specific"),
                "relevant": query["relevant"],
                "hit_at_1": cos_rank[0] in relevant,
                "margin_cosine": round(float(cos_sorted[0] - cos_sorted[1]), 4),
                # On a different scale from the cosine margin: CSLS doubles the
                # similarity term, so the two margins are not comparable.
                "margin_csls": round(float(csls_sorted[0] - csls_sorted[1]), 4),
                "top_score": round(float(cos_sorted[0]), 4),
                "cosine": [
                    {
                        "doc": doc_id,
                        "score": round(float(qd[qi, doc_index[doc_id]]), 4),
                        "relevant": doc_id in relevant,
                        "generic": doc_id in generic_ids,
                    }
                    for doc_id in cos_rank[:K_RETRIEVAL]
                ],
                "csls": [
                    {
                        "doc": doc_id,
                        "score": round(float(qd_csls[qi, doc_index[doc_id]]), 4),
                        "relevant": doc_id in relevant,
                        "generic": doc_id in generic_ids,
                        "cosine_rank": cos_positions[doc_id] + 1,
                    }
                    for doc_id in csls_rank[:K_RETRIEVAL]
                ],
            }
        )

    n_slots = len(queries) * K_RETRIEVAL
    generic_idx = [doc_index[i] for i in generic_ids]

    styles: dict[str, list[int]] = {}
    for qi, row in enumerate(query_rows):
        styles.setdefault(row["style"], []).append(qi)

    result = {
        "meta": {
            "model": MODEL_NAME,
            "dimension": int(doc_emb.shape[1]),
            "n_documents": n_docs,
            "n_queries": len(queries),
            "k_retrieval": K_RETRIEVAL,
            "k_csls": K_CSLS,
            "k_values": list(K_VALUES),
            "seed": SEED,
            "normalized": True,
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "torch": torch.__version__,
                "sentence_transformers": __import__("sentence_transformers").__version__,
            },
        },
        "topics": corpus["meta"]["topics"],
        "documents": [
            {
                "id": d["id"],
                "topic": d["topic"],
                "title": d["title"],
                "text": d["text"],
                "mean_cosine": round(float(mean_cos[i]), 4),
                "cos_centroid": round(float(cos_centroid[i]), 4),
                "r_doc": round(float(r_doc[i]), 4),
                "n_query_top5": int(query_top_counts[i]),
                "n_query_top5_csls": int(csls_top_counts[i]),
            }
            for i, d in enumerate(docs)
        ],
        "document_side": {
            "per_k": per_k,
            "mean_cosine_overall": round(float(mean_cos.mean()), 4),
            "mean_cosine_min": round(float(mean_cos.min()), 4),
            "mean_cosine_max": round(float(mean_cos.max()), 4),
        },
        "query_side": {
            "k": K_RETRIEVAL,
            "counts": {doc_ids[i]: int(query_top_counts[i]) for i in range(n_docs)},
            "counts_csls": {doc_ids[i]: int(csls_top_counts[i]) for i in range(n_docs)},
            "skewness": round(skewness(query_top_counts), 3),
            "skewness_csls": round(skewness(csls_top_counts), 3),
            "max_count": int(query_top_counts.max()),
            "documents_never_retrieved": int((query_top_counts == 0).sum()),
            "generic_slot_share": round(float(query_top_counts[generic_idx].sum() / n_slots), 4),
            "generic_slot_share_csls": round(float(csls_top_counts[generic_idx].sum() / n_slots), 4),
        },
        "queries": query_rows,
        "metrics": {
            "k": K_RETRIEVAL,
            "cosine": {k: round(v, 4) for k, v in mean_metrics(cosine_eval).items()},
            "csls": {k: round(v, 4) for k, v in mean_metrics(csls_eval).items()},
            "mean_margin_cosine": round(float(np.mean([q["margin_cosine"] for q in query_rows])), 4),
            "mean_margin_csls": round(float(np.mean([q["margin_csls"] for q in query_rows])), 4),
            # Does the rank-1/rank-2 gap say anything about whether rank 1 is
            # right? Compared against the top score, which is the number a
            # similarity threshold would actually use.
            "margin_vs_correctness": {
                verdict: {
                    "n": len(group),
                    "mean_margin": round(float(np.mean([q["margin_cosine"] for q in group])), 4),
                    "median_margin": round(float(np.median([q["margin_cosine"] for q in group])), 4),
                    "mean_top_score": round(float(np.mean([q["top_score"] for q in group])), 4),
                }
                for verdict, group in {
                    "hit": [q for q in query_rows if q["hit_at_1"]],
                    "miss": [q for q in query_rows if not q["hit_at_1"]],
                }.items()
                if group
            },
            "by_style": {
                style: {
                    "n": len(idx),
                    "cosine": {k: round(v, 4) for k, v in mean_metrics([cosine_eval[i] for i in idx]).items()},
                    "csls": {k: round(v, 4) for k, v in mean_metrics([csls_eval[i] for i in idx]).items()},
                    "mean_margin_cosine": round(
                        float(np.mean([query_rows[i]["margin_cosine"] for i in idx])), 4
                    ),
                }
                for style, idx in styles.items()
            },
        },
        "matrix": {
            "queries": [q["id"] for q in queries],
            "documents": doc_ids,
            "cosine": [round_list(row, 3) for row in qd],
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")

    # ---- console summary -------------------------------------------------
    print(f"model {MODEL_NAME} · {n_docs} documents · {len(queries)} queries")
    print(f"mean pairwise cosine {mean_cos.mean():.3f}")
    print("\ndocument-to-document neighbour graph")
    for k in K_VALUES:
        row = per_k[str(k)]
        print(
            f"  k={k:<3} skew(N_k) {row['skewness']:>5.2f} -> {row['skewness_csls']:>5.2f}   "
            f"max N_k {row['max_count']:>3} -> {row['max_count_csls']:<3}  "
            f"never a neighbour {row['zero_count']:>3} -> {row['zero_count_csls']:<3}  "
            f"reciprocal {row['reciprocal_rate']:.2f} -> {row['reciprocal_rate_csls']:.2f}  "
            f"cross-topic {row['cross_topic_rate']:.2f}  "
            f"corr(N_k, centroid) {row['corr_centroid']:>5.2f}"
        )
    hub_order = sorted(range(n_docs), key=lambda i: -per_k["10"]["counts"][doc_ids[i]])[:5]
    print("\n  top documents by N_10: " + ", ".join(f"{doc_ids[i]} ({per_k['10']['counts'][doc_ids[i]]})" for i in hub_order))

    qs = result["query_side"]
    print(f"\nquery-to-document retrieval (k={K_RETRIEVAL})")
    print(
        f"  slot skewness {qs['skewness']:.2f} -> {qs['skewness_csls']:.2f} with CSLS; "
        f"generic share {qs['generic_slot_share']:.2%} -> {qs['generic_slot_share_csls']:.2%}; "
        f"never retrieved {qs['documents_never_retrieved']}"
    )
    for name in ("cosine", "csls"):
        m = result["metrics"][name]
        print(
            f"  {name:<7} P@1 {m['p_at_1']:.3f}  P@5 {m['p_at_k']:.3f}  "
            f"R@5 {m['recall_at_k']:.3f}  MRR {m['mrr']:.3f}  nDCG@5 {m['ndcg_at_k']:.3f}"
        )
    for verdict, row in result["metrics"]["margin_vs_correctness"].items():
        print(
            f"  rank-1 {verdict:<5} (n={row['n']:>2})  mean margin {row['mean_margin']:.3f}  "
            f"median {row['median_margin']:.3f}  mean top score {row['mean_top_score']:.3f}"
        )
    for style, row in result["metrics"]["by_style"].items():
        print(
            f"  {style:<9} (n={row['n']:>2})  P@1 {row['cosine']['p_at_1']:.3f} -> {row['csls']['p_at_1']:.3f}  "
            f"nDCG@5 {row['cosine']['ndcg_at_k']:.3f} -> {row['csls']['ndcg_at_k']:.3f}  "
            f"margin {row['mean_margin_cosine']:.3f}"
        )
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
