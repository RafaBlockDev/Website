# Embedding hubness experiment

Supporting code for the notebook entry
[*When the Nearest Neighbor Is Everyone's Neighbor*](https://rafablockdev.github.io/notebook/when-the-nearest-neighbor-is-everyones-neighbor/).

The experiment encodes a fixed 50-document corpus with a sentence-embedding
model and measures the neighbour structure of the resulting space: k-occurrence
counts and their skewness, reciprocal-neighbour rate, cross-topic in-degree,
rank-1/rank-2 margins, and what a CSLS local-density correction changes on both
the document graph and query-to-document retrieval.

Every number in the article comes from the JSON this writes. Nothing in it is
estimated, rounded by hand, or filled in afterwards.

## Files

| Path | Contents |
| :-- | :-- |
| `corpus.json` | 50 documents across seven topics, plus 24 queries with hand-assigned relevance labels. Labels were fixed before anything was embedded. |
| `experiment.py` | Encoding, similarity, neighbour statistics, CSLS, retrieval evaluation, and the 2-D PCA layout used by one figure. |
| `requirements.txt` | Pinned package versions used for the checked-in results. |

The single output is `src/data/embedding-hubness/hubness.json` in the site
source tree, which the article imports at build time. Nothing here runs during
the Astro build.

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Keeps the model download inside this directory instead of ~/.cache.
HF_HOME="$PWD/.hf-cache" .venv/bin/python experiment.py
```

The first run downloads `sentence-transformers/all-MiniLM-L6-v2` (about 87 MB).
Afterwards it runs offline in a few seconds on CPU. `--out` redirects the
output; `--corpus` points at a different corpus file.

`.venv/` and `.hf-cache/` are ignored by git — model weights and virtual
environments are never committed.

## Reproducibility

Seeds are fixed and PyTorch is put in deterministic mode; the PCA components
are sign-fixed so the projection does not flip between runs. Re-running on the
same machine reproduces the JSON byte for byte. Across CPU architectures or
package versions the last decimal of a similarity can move, which is enough to
swap two documents that are already nearly tied — the aggregate statistics are
stable, individual near-ties are not. That instability is itself one of the
article's points.

## Scope

Fifty short documents, one encoder, one language, one set of hand-written
relevance labels. The measurements are real, and they describe this corpus with
this model. They are a demonstration of a method, not evidence about embedding
spaces in general.
