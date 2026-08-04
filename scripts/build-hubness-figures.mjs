#!/usr/bin/env node
// Derives small, frontend-friendly JSON files for each article figure from
// the full experiment output. Pure derivation: no numbers are computed here
// that aren't already in hubness.json, only reshaped and trimmed.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const SRC = path.join(ROOT, 'src', 'data', 'embedding-hubness', 'hubness.json');
const OUT_DIR = path.join(ROOT, 'src', 'data', 'embedding-hubness', 'figures');

const data = JSON.parse(readFileSync(SRC, 'utf-8'));

mkdirSync(OUT_DIR, { recursive: true });

function shortLabel(title, max = 34) {
  if (title.length <= max) return title;
  const cut = title.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return `${cut.slice(0, lastSpace > 12 ? lastSpace : max)}…`;
}

function write(name, obj) {
  writeFileSync(path.join(OUT_DIR, name), JSON.stringify(obj, null, 1) + '\n', 'utf-8');
  console.log(`wrote figures/${name}`);
}

const docsById = Object.fromEntries(data.documents.map((d) => [d.id, d]));

// 1. Neighbor occurrence chart: top 10 documents by N5, k=5.
{
  const K = '5';
  const counts = data.document_side.per_k[K].counts;
  const ranked = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([id, count]) => ({
      id,
      label: shortLabel(docsById[id].title),
      title: docsById[id].title,
      topic: docsById[id].topic,
      count
    }));
  const hubThreshold = data.document_side.per_k[K].mean_count * 2;
  for (const row of ranked) row.isHub = row.count >= hubThreshold;

  write('occurrence.json', {
    k: Number(K),
    expected: data.document_side.per_k[K].mean_count,
    hubThreshold,
    documents: ranked
  });
}

// 2. Cross-topic growth by k.
{
  const points = data.meta.k_values.map((k) => ({
    k,
    crossTopicRate: data.document_side.per_k[String(k)].cross_topic_rate
  }));
  write('cross-topic-by-k.json', { points });
}

// 3. Reciprocity and hubness before/after CSLS, at k=5.
{
  const K = '5';
  const row = data.document_side.per_k[K];
  write('before-after.json', {
    k: Number(K),
    metrics: [
      { key: 'skewness', label: 'Skewness of N₅', before: row.skewness, after: row.skewness_csls, digits: 2 },
      { key: 'max_n5', label: 'Maximum N₅', before: row.max_count, after: row.max_count_csls, digits: 0 },
      { key: 'never_neighbor', label: 'Never a neighbor', before: row.zero_count, after: row.zero_count_csls, digits: 0 },
      { key: 'reciprocity', label: 'Reciprocity', before: row.reciprocal_rate, after: row.reciprocal_rate_csls, digits: 2 }
    ]
  });
}

// 4. Retrieval metrics before/after CSLS, 0-1 scale.
{
  const m = data.metrics;
  write('retrieval-metrics.json', {
    k: m.k,
    metrics: [
      { key: 'p_at_1', label: 'Precision@1', cosine: m.cosine.p_at_1, csls: m.csls.p_at_1 },
      { key: 'mrr', label: 'MRR', cosine: m.cosine.mrr, csls: m.csls.mrr },
      { key: 'ndcg_at_5', label: 'nDCG@5', cosine: m.cosine.ndcg_at_k, csls: m.csls.ndcg_at_k }
    ]
  });
}

// 5. Rank-1 margin analysis, per query.
{
  const queries = data.queries.map((q) => ({
    id: q.id,
    margin: q.margin_cosine,
    topScore: q.top_score,
    hit: q.hit_at_1,
    style: q.style
  }));
  write('margins.json', {
    queries,
    summary: data.metrics.margin_vs_correctness
  });
}

// 6. Query-style comparison.
{
  const styles = Object.entries(data.metrics.by_style).map(([style, row]) => ({
    style,
    n: row.n,
    ndcgCosine: row.cosine.ndcg_at_k,
    ndcgCsls: row.csls.ndcg_at_k,
    meanMargin: row.mean_margin_cosine
  }));
  write('query-style.json', { styles });
}

// 7. Similarity matrix (secondary evidence).
{
  const queryKeys = data.queries.map((q, i) => ({
    row: `Q${String(i + 1).padStart(2, '0')}`,
    id: q.id,
    text: q.text,
    style: q.style
  }));
  const documents = data.matrix.documents.map((id) => ({
    id,
    label: shortLabel(docsById[id].title, 22),
    topic: docsById[id].topic
  }));
  const cells = [];
  data.matrix.cosine.forEach((row, qi) => {
    row.forEach((value, di) => {
      cells.push({ row: queryKeys[qi].row, doc: documents[di].id, value });
    });
  });
  write('matrix.json', { queryKeys, documents, cells });
}

// 8. Three worked examples: repaired, regressed, unresolved.
{
  const ids = { repaired: 'q-chunk-size', regressed: 'q-vram-long-context', unresolved: 'q-ci-local' };
  const examples = Object.fromEntries(
    Object.entries(ids).map(([kind, id]) => {
      const q = data.queries.find((row) => row.id === id);
      return [
        kind,
        {
          id: q.id,
          text: q.text,
          relevant: q.relevant,
          marginCosine: q.margin_cosine,
          marginCsls: q.margin_csls,
          cosine: q.cosine.map((c) => ({ ...c, title: docsById[c.doc].title })),
          csls: q.csls.map((c) => ({ ...c, title: docsById[c.doc].title }))
        }
      ];
    })
  );
  write('examples.json', examples);
}

console.log(`\nderived ${8} figure files from ${path.relative(ROOT, SRC)}`);
