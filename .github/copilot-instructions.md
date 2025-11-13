### Quick context for AI contributors

This repository is a small, inventory-driven Data Quality (DQ) toolkit and a Dash UI.
The inventory (streams/projects/zones/datasets) drives dataset selection and DQ definitions.
Key patterns and entry points are listed below so an AI agent can be productive quickly.

---

1) Big picture (what to modify and why)

- Inventory is the source of truth: `config/inventory.yaml`. Many helpers expect dataset "aliases" to be present in DQ definitions (see `dq/definitions/*`).
- CLI helpers live under `tools/`:
  - `tools/create_dq_from_inventory.py` — generate a DQ YAML from inventory aliases.
  - `tools/run_dq.py` — run a DQ definition file.
- The dashboard app is a standard Dash app; the local runner is `run.py` which imports `app` from `app.py`.

2) Core code and important files

- `src/config.py` — loads `config/inventory.yaml`, exposes `STREAMS`, `DATASET_MAPPING`, and environment flags. Important env vars:
  - `DQ_DEBUG_UI` (enable debug UI behavior),
  - `DQ_DEFAULT_STREAM`, `DQ_DEFAULT_PROJECT`, `DQ_DEFAULT_ZONE`.
  - The code tries to import `dataiku` and falls back to `dataiku_stub` so you can run locally without Dataiku.
- `src/inventory.py` — utility functions to query streams, projects, zones and datasets. Use these to look up aliases and dataset metadata.
- `dq/definitions/*.yaml` — DQ definitions. They MUST reference dataset aliases (not raw paths).
- `src/dq_runner.py` — small runner which executes `metrics` then `tests` described in a config dict. Use it as the canonical example of how metrics/tests are wired.
- `src/metrics.py` and `src/plugins/` — metric implementations and plugin/test contracts. Look at `tests/` under `src/plugins/tests` for plugin examples.

3) Developer workflows & commands

- Run the Dash app locally:

  ```powershell
  python run.py
  ```

- Create a DQ YAML from inventory (example):

  ```powershell
  python tools/create_dq_from_inventory.py --id my_dq --aliases sales_2024 customers --out dq/definitions/my_dq.yaml
  ```

- Run a DQ definition (example):

  ```powershell
  python tools/run_dq.py --dq dq/definitions/sales_quality_v1.yaml
  python tools/run_dq.py --dq dq/definitions/sales_quality_v1.yaml --override sales_2024=sourcing/input/sales_2024_alt.csv
  ```

- Tests: repo uses plain pytest-style tests under `tests/` and `src/plugins/tests`. Run them from repo root:

  ```powershell
  pytest -q
  # or a single test file
  pytest tests/test_dq_runner.py -q
  ```

4) Project-specific conventions / pitfalls

- Inventory-driven: DQ definitions reference dataset aliases (field `alias`). When adding features, prefer alias-based lookups via `src/inventory.py` / `src/config.py`.
- `config._load_inventory()` strips Markdown-style ``` fences from YAML (inventory may contain fenced content). Keep that behaviour in mind when editing inventory.
- Dataiku integration is optional: code uses `dataiku_stub.py` when real Dataiku SDK is missing. Avoid relying on live Dataiku in quick unit tests.
- Tests add repo root to `sys.path` (see `tests/test_dq_runner.py`). When running programmatically, ensure imports resolve from repo root.

5) Integration points & external dependencies

- Dataiku SDK (`dataiku`) — optional. `src/config.py` calls `dataiku.api_client()` when available.
- PySpark may be used in parts of the project (requirements include `pyspark`). Plugins may rely on Spark contexts under `src/context/`.
- Connectors: local CSV/Parquet connectors are available under the app; other connectors (SharePoint, Dataiku) are scaffolded.

6) How code is typically structured for changes

- Small feature or metric: add implementation in `src/metrics.py` or `src/plugins/*`, add small unit tests under `tests/` or `src/plugins/tests/`.
- UI change: update Dash layouts in `app.py` and supporting `ui/` files; `run.py` runs the app locally for manual testing.

7) Examples to reference when coding

- Minimal metric/test config used by `src/dq_runner.py`:

  ```py
  cfg = {
    "metrics": [{"id":"m1","type":"missing_rate","column":"col"}],
    "tests": [{"id":"t1","type":"range","metric":"m1","low":0,"high":0.1}]
  }
  ```

8) If you update this file

- If `.github/copilot-instructions.md` already exists, merge gently: preserve human-authored guidance. This repository had none when this file was added.

---

If any area above is unclear or you'd like me to add short examples for a particular subsystem (plugins, inventory schema, or Dataiku stubs), tell me which area and I'll expand the doc.
