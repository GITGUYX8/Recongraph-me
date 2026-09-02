# ReconGraph: V1 Certified Core

ReconGraph is a deterministic, graph-based reconciliation engine for Indian GST compliance. It processes Purchase Registers (PR) and GST Returns (GSTR-2B) to find exact matches and categorize mismatches into a human review queue based on a "missing vs contradictory" semantic paradigm.

**Live demo:** _add your Vercel URL here after deploying (see [DEPLOYMENT.md](DEPLOYMENT.md))_

## V1 Certification Status
"V1 Certified" refers to the engine core's correctness status (see below), tracked
independently from the package's semantic version (`pyproject.toml`, currently
`2.0.0` — see [CHANGELOG.md](CHANGELOG.md) for what shipped in each release).
The engine core is officially **V1 Certified**.
- All mathematical proofs pass.
- Challenge Referee (Adversarial Negatives) is green with 0 False Positives.
- Default Auto-Match Threshold is calibrated at `0.95`, keeping adversarial recall tight while maximizing throughput on noisy real-world gaps (±₹1 rounding, minor date drifts).
- Strict conservation bounds: `input records == output records`. No data loss.

## Running the UI Dashboard

ReconGraph ships with a React/Next.js dashboard to visualize the review queue and engine rationale.

```bash
# Terminal 1: Next.js Frontend
cd recongraph-ui
npm install
npm run dev
# The UI will load at http://localhost:3000
```

The UI includes a static demo fallback so you can instantly view the adversarial Challenge Dataset without starting the Python backend.

To process new datasets, you may start the FastAPI backend:
```bash
# Terminal 2: FastAPI Backend
pip install -e .
pip install -r recongraph-api/requirements.txt
python -m uvicorn recongraph-api.app.main:app --reload --env-file recongraph-api/.env
```

## Documentation
- [BENCHMARKS.md](BENCHMARKS.md): Precision/Recall characteristics on synthetic and adversarial corpora.
- [ADR-009 Stage 8 Residue](docs/ADR-009-stage-8-residue.md): Documentation of module isolation and engine boundaries.
