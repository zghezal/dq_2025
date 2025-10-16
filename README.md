

---
## Inventory → Streams/Projects/Zones/Datasets → DQ
- L'inventaire est dans `config/inventory.yaml` et référence les **aliases** de datasets.
- Les définitions DQ (`dq/definitions/*.yaml`) **ne** référencent **que des aliases**.
- Créer un DQ basé sur l'inventaire :
  ```bash
  python tools/create_dq_from_inventory.py --id my_dq --aliases sales_2024 customers --out dq/definitions/my_dq.yaml
  ```
- Exécuter un DQ (avec overrides d’alias si besoin) :
  ```bash
  python tools/run_dq.py --dq dq/definitions/sales_quality_v1.yaml
  python tools/run_dq.py --dq dq/definitions/sales_quality_v1.yaml --override sales_2024=sourcing/input/sales_2024_alt.csv
  ```
- Connecteur **local** (CSV/Parquet) fourni; Dataiku/SharePoint sont prêts à être branchés.

### Dépendances
- **Un seul** `requirements.txt` consolidé à la racine.
- Les `requirements*.txt` historiques sont déplacés vers `attached_assets/legacy_requirements/`.
