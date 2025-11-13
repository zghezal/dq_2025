# 🚀 Quick Start - Sources de Données Multiples

## En 60 secondes

### 1. Importer les modules

```python
from src.core.models_channels import (
    FileSpecification, 
    DataSourceType, 
    FileFormat
)
from src.connectors import ConnectorFactory
```

### 2. Créer une FileSpecification

#### 🗂️ Fichier Local

```python
spec = FileSpecification(
    file_id='my_file',
    name='Mon Fichier',
    source_type=DataSourceType.LOCAL,
    format=FileFormat.CSV,
    connection_params={
        'file_path': 'c:/data/file.csv',
        'format': 'csv'
    }
)
```

#### 🐘 HUE (HDFS/Hive)

```python
spec = FileSpecification(
    file_id='hue_data',
    name='Données HUE',
    source_type=DataSourceType.HUE,
    format=FileFormat.CSV,
    connection_params={
        'hue_url': 'http://hue.company.com:8888',
        'auth_token': os.environ['HUE_TOKEN'],
        'query': 'SELECT * FROM my_table',
        'database': 'prod'
    }
)
```

#### 📁 SharePoint

```python
spec = FileSpecification(
    file_id='sp_file',
    name='Fichier SharePoint',
    source_type=DataSourceType.SHAREPOINT,
    format=FileFormat.EXCEL,
    connection_params={
        'site_url': 'https://company.sharepoint.com/sites/data',
        'folder_path': '/Shared Documents/Files',
        'file_name': 'data.xlsx',
        'access_token': os.environ['SP_TOKEN'],
        'format': 'xlsx'
    }
)
```

#### 🔷 Dataiku Dataset

```python
spec = FileSpecification(
    file_id='dku_dataset',
    name='Dataset Dataiku',
    source_type=DataSourceType.DATAIKU_DATASET,
    format=FileFormat.CSV,
    connection_params={
        'project_key': 'MY_PROJECT',
        'dataset_name': 'my_dataset',
        'sampling': 'head',
        'limit': 10000
    }
)
```

### 3. Utiliser le Connecteur

```python
# Créer le connecteur
connector = ConnectorFactory.create_connector(
    spec.source_type,
    spec.connection_params
)

# Tester la connexion
success, message = connector.test_connection()
print(message)

# Charger les données
if success:
    df = connector.fetch_data()
    print(f"✅ {len(df)} lignes chargées")
```

---

## Paramètres Essentiels par Type

### LOCAL
- `file_path` : Chemin du fichier
- `format` : csv, xlsx, parquet, json, tsv

### HUE
- `hue_url` : URL de HUE
- `auth_token` OU `username`+`password`
- `path` (fichier HDFS) OU `query` (Hive)

### SHAREPOINT
- `site_url` : URL du site
- `folder_path` : Chemin du dossier
- `file_name` : Nom du fichier
- `access_token` OU `client_id`+`client_secret`

### DATAIKU_DATASET
- `project_key` : Clé projet Dataiku
- `dataset_name` : Nom du dataset
- `sampling` : head, random, full (optionnel)

---

## Test Rapide

```powershell
# Tester tous les connecteurs
python demo_data_sources.py

# Tester l'import
python -c "from src.connectors import *; print('OK')"
```

---

## Troubleshooting Express

| Erreur | Solution |
|--------|----------|
| Module not found | `pip install pandas requests` |
| Timeout HUE | Vérifier URL et network |
| Auth SharePoint | Token expiré → régénérer |
| Dataiku stub mode | Normal en local (pas de SDK) |

---

## Documentation Complète

- **Guide détaillé** : `DATA_SOURCES_DOC.md`
- **Migration** : `MIGRATION_GUIDE.md`
- **Statut** : `DATA_SOURCES_READY.md`

---

**Prêt à l'emploi** ✅
