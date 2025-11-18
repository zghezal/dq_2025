# 📚 Système de Sources de Données Multiples

## Vue d'ensemble

Le système de canaux DQ supporte maintenant **4 types de sources de données** :

| Type | Description | Use Case |
|------|-------------|----------|
| 🗂️ **LOCAL** | Fichier local uploadé | Upload direct via l'interface web |
| 🐘 **HUE** | HDFS/Hive via HUE | Accès aux données Big Data sur le cluster |
| 📁 **SHAREPOINT** | SharePoint Online | Récupération depuis bibliothèques de documents |
| 🔷 **DATAIKU_DATASET** | Dataset Dataiku existant | Réutilisation de datasets déjà préparés |

---

## Architecture

### Structure des Connecteurs

```
src/connectors/
├── __init__.py
├── base.py                    # Interface DataConnector (ABC)
├── local_connector.py         # Fichiers locaux
├── hue_connector.py          # HUE (HDFS/Hive)
├── sharepoint_connector.py   # SharePoint Online
├── dataiku_connector.py      # Datasets Dataiku
└── factory.py                # ConnectorFactory
```

### Modèle de Données

**FileSpecification** étendu avec :

```python
@dataclass
class FileSpecification:
    # ... champs existants ...
    
    # Nouveaux champs
    source_type: DataSourceType = DataSourceType.LOCAL
    connection_params: Dict[str, Any] = field(default_factory=dict)
```

---

## 🗂️ 1. LOCAL - Fichiers Locaux

### Paramètres Requis

```python
connection_params = {
    'file_path': '/path/to/file.csv',  # Chemin absolu
    'format': 'csv'                     # csv, xlsx, parquet, json, tsv
}
```

### Paramètres Optionnels

```python
# Pour CSV
connection_params = {
    # ...
    'csv_options': {
        'sep': ',',
        'encoding': 'utf-8',
        'decimal': '.',
        # Tous les paramètres de pandas.read_csv()
    }
}

# Pour Excel
connection_params = {
    # ...
    'sheet_name': 'Sheet1'  # ou 0 pour la première feuille
}
```

### Exemple d'utilisation

```python
from src.core.models_channels import DataSourceType, FileSpecification

spec = FileSpecification(
    file_id='sales_file',
    name='Fichier des ventes',
    source_type=DataSourceType.LOCAL,
    format=FileFormat.CSV,
    connection_params={
        'file_path': 'c:/data/sales.csv',
        'format': 'csv',
        'csv_options': {'sep': ';', 'encoding': 'utf-8'}
    }
)
```

---

## 🐘 2. HUE - HDFS/Hive

### Paramètres Requis

```python
connection_params = {
    'hue_url': 'http://hue.example.com:8888',
    
    # Authentification (au choix)
    'auth_token': 'your_token',  # OU
    'username': 'user',
    'password': 'pass',
    
    # Source (au choix)
    'path': '/user/data/sales.csv',  # Fichier HDFS, OU
    'query': 'SELECT * FROM sales'   # Requête Hive/Impala
}
```

### Paramètres Optionnels

```python
connection_params = {
    # ...
    'database': 'default',  # Base de données Hive
    'format': 'csv'         # Format pour fichiers HDFS
}
```

### Exemple - Fichier HDFS

```python
spec = FileSpecification(
    file_id='hdfs_sales',
    name='Ventes sur HDFS',
    source_type=DataSourceType.HUE,
    format=FileFormat.CSV,
    connection_params={
        'hue_url': 'http://hue.mycompany.com:8888',
        'auth_token': os.environ['HUE_TOKEN'],
        'path': '/user/dataeng/sales_2024.csv',
        'format': 'csv'
    }
)
```

### Exemple - Requête Hive

```python
spec = FileSpecification(
    file_id='hive_agg',
    name='Agrégations Hive',
    source_type=DataSourceType.HUE,
    format=FileFormat.CSV,
    connection_params={
        'hue_url': 'http://hue.mycompany.com:8888',
        'username': 'dataeng',
        'password': os.environ['HUE_PASSWORD'],
        'query': '''
            SELECT 
                product_id,
                SUM(amount) as total_amount
            FROM sales
            WHERE year = 2024
            GROUP BY product_id
        ''',
        'database': 'prod'
    }
)
```

---

## 📁 3. SHAREPOINT - SharePoint Online

### Paramètres Requis

```python
connection_params = {
    'site_url': 'https://tenant.sharepoint.com/sites/mysite',
    'folder_path': '/Shared Documents/Data',
    'file_name': 'sales_2024.xlsx',
    
    # Authentification (au choix)
    'access_token': 'your_token',  # OU
    'client_id': 'app_client_id',
    'client_secret': 'app_secret'
}
```

### Paramètres Optionnels

```python
connection_params = {
    # ...
    'format': 'xlsx',
    'sheet_name': 'Data'  # Pour Excel
}
```

### Exemple - OAuth2 (recommandé)

```python
spec = FileSpecification(
    file_id='sp_sales',
    name='Ventes SharePoint',
    source_type=DataSourceType.SHAREPOINT,
    format=FileFormat.EXCEL,
    connection_params={
        'site_url': 'https://mycompany.sharepoint.com/sites/DataQuality',
        'folder_path': '/Shared Documents/Deposits/Sales',
        'file_name': 'sales_monthly_2024.xlsx',
        'client_id': os.environ['SP_CLIENT_ID'],
        'client_secret': os.environ['SP_CLIENT_SECRET'],
        'format': 'xlsx',
        'sheet_name': 'Sales'
    }
)
```

### Exemple - Token direct

```python
spec = FileSpecification(
    file_id='sp_customers',
    name='Clients SharePoint',
    source_type=DataSourceType.SHAREPOINT,
    format=FileFormat.CSV,
    connection_params={
        'site_url': 'https://mycompany.sharepoint.com/sites/CRM',
        'folder_path': '/Lists/Customers/Exports',
        'file_name': 'customers_latest.csv',
        'access_token': os.environ['SP_ACCESS_TOKEN'],
        'format': 'csv'
    }
)
```

---

## 🔷 4. DATAIKU_DATASET - Datasets Dataiku

### Paramètres Requis

```python
connection_params = {
    'project_key': 'DKU_PROJECT',
    'dataset_name': 'sales_cleaned'
}
```

### Paramètres Optionnels

```python
connection_params = {
    # ...
    'sampling': 'head',           # 'head', 'random', 'full'
    'limit': 10000,               # Nombre de lignes max
    'columns': ['col1', 'col2']   # Colonnes spécifiques
}
```

### Exemple - Dataset complet

```python
spec = FileSpecification(
    file_id='dku_sales',
    name='Sales Cleaned (Dataiku)',
    source_type=DataSourceType.DATAIKU_DATASET,
    format=FileFormat.CSV,  # Ignoré pour Dataiku
    connection_params={
        'project_key': 'DQ_PROD',
        'dataset_name': 'sales_cleaned_v2',
        'sampling': 'full'  # Charger tout le dataset
    }
)
```

### Exemple - Échantillon aléatoire

```python
spec = FileSpecification(
    file_id='dku_customers_sample',
    name='Customers Sample',
    source_type=DataSourceType.DATAIKU_DATASET,
    format=FileFormat.CSV,
    connection_params={
        'project_key': 'CRM',
        'dataset_name': 'customers_master',
        'sampling': 'random',
        'limit': 5000,
        'columns': ['customer_id', 'name', 'segment', 'revenue']
    }
)
```

---

## 🔧 Utilisation Programmatique

### Factory Pattern

```python
from src.core.models_channels import DataSourceType
from src.connectors.factory import ConnectorFactory

# Créer un connecteur
connector = ConnectorFactory.create_connector(
    source_type=DataSourceType.LOCAL,
    connection_params={'file_path': '/data/sales.csv', 'format': 'csv'}
)

# Tester la connexion
success, message = connector.test_connection()
if success:
    # Charger les données
    df = connector.fetch_data()
    print(f"Loaded {len(df)} rows")
```

### Avec FileSpecification

```python
from src.connectors.factory import ConnectorFactory

spec = FileSpecification(...)  # Voir exemples ci-dessus

# Créer le connecteur depuis la spec
connector = ConnectorFactory.create_connector(
    source_type=spec.source_type,
    connection_params=spec.connection_params
)

# Utiliser le connecteur
df = connector.fetch_data()
```

---

## 🎯 Intégration dans les Canaux

### Configuration d'un Canal Multi-Sources

```python
from src.core.models_channels import DropChannel, FileSpecification, DataSourceType

channel = DropChannel(
    channel_id='multi_source_channel',
    name='Canal Multi-Sources',
    file_specifications=[
        # Fichier local uploadé
        FileSpecification(
            file_id='local_upload',
            name='Upload Manuel',
            source_type=DataSourceType.LOCAL,
            required=True
        ),
        
        # Fichier depuis SharePoint
        FileSpecification(
            file_id='sp_reference',
            name='Référentiel SharePoint',
            source_type=DataSourceType.SHAREPOINT,
            required=True,
            connection_params={
                'site_url': 'https://company.sharepoint.com/sites/ref',
                'folder_path': '/Shared Documents/Reference',
                'file_name': 'products.xlsx',
                'access_token': os.environ['SP_TOKEN'],
                'format': 'xlsx'
            }
        ),
        
        # Dataset Dataiku
        FileSpecification(
            file_id='dku_history',
            name='Historique (Dataiku)',
            source_type=DataSourceType.DATAIKU_DATASET,
            required=False,
            connection_params={
                'project_key': 'HISTORY',
                'dataset_name': 'sales_history',
                'sampling': 'head',
                'limit': 100000
            }
        )
    ]
)
```

---

## ✅ Tests et Validation

### Script de Test

Exécuter le script de démonstration :

```powershell
python demo_data_sources.py
```

### Tests Unitaires

```python
import pytest
from src.connectors.factory import ConnectorFactory
from src.core.models_channels import DataSourceType

def test_local_connector():
    connector = ConnectorFactory.create_connector(
        DataSourceType.LOCAL,
        {'file_path': 'test.csv', 'format': 'csv'}
    )
    assert connector is not None
    
def test_connector_validation():
    connector = ConnectorFactory.create_connector(
        DataSourceType.SHAREPOINT,
        {'site_url': 'https://test.sharepoint.com'}
    )
    is_valid, error = connector.validate_connection()
    assert not is_valid  # Paramètres incomplets
    assert 'folder_path' in error
```

---

## 🔐 Sécurité et Bonnes Pratiques

### Gestion des Credentials

**❌ NE JAMAIS** :
```python
# Mauvais - credentials en dur
connection_params = {
    'password': 'mon_mot_de_passe'  # ❌
}
```

**✅ TOUJOURS** :
```python
# Bon - variables d'environnement
import os
connection_params = {
    'password': os.environ.get('HUE_PASSWORD')  # ✅
}
```

### Filtrage dans get_metadata()

Les connecteurs masquent automatiquement les credentials sensibles :

```python
metadata = connector.get_metadata()
# Les champs 'password', 'token', 'auth_token' sont exclus
```

---

## 📊 Diagramme de Flux

```
┌─────────────────┐
│  User Interface │
└────────┬────────┘
         │ Sélectionne source + params
         ▼
┌─────────────────────┐
│ FileSpecification   │
│ - source_type       │
│ - connection_params │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ ConnectorFactory    │
│ .create_connector() │
└────────┬────────────┘
         │
         ▼
    ┌────────────────────────┐
    │   DataConnector        │
    │ ┌─────────────────────┐│
    │ │ validate_connection ││
    │ │ test_connection     ││
    │ │ fetch_data         ││
    │ └─────────────────────┘│
    └───┬────────────────────┘
        │
   ┌────┴────────┬──────────┬────────────┐
   ▼             ▼          ▼            ▼
┌──────┐  ┌─────────┐  ┌────────┐  ┌────────┐
│LOCAL │  │   HUE   │  │SharePt │  │Dataiku │
└──────┘  └─────────┘  └────────┘  └────────┘
   │             │          │            │
   └─────────────┴──────────┴────────────┘
                 │
                 ▼
          ┌──────────────┐
          │ pd.DataFrame │
          └──────────────┘
```

---

## 📝 TODO / Améliorations Futures

- [ ] Ajouter interface UI pour configurer les sources dans channel_admin
- [ ] Implémenter cache pour les données Dataiku fréquemment utilisées
- [ ] Ajouter support Azure Blob Storage
- [ ] Ajouter support AWS S3
- [ ] Ajouter support FTP/SFTP
- [ ] Améliorer gestion des erreurs réseau (retry, timeout configurable)
- [ ] Ajouter logs détaillés pour audit
- [ ] Implémenter chiffrement pour les credentials stockés

---

## 🆘 Troubleshooting

### Erreur: "Module dataiku not found"

**Solution** : Mode stub activé automatiquement pour développement local.

### Erreur: "Timeout lors de la connexion à HUE"

**Solutions** :
- Vérifier que l'URL HUE est accessible
- Augmenter le timeout dans le connecteur
- Vérifier les credentials

### Erreur: "Erreur d'authentification SharePoint"

**Solutions** :
- Vérifier que le token n'est pas expiré
- Régénérer le `access_token`
- Vérifier les permissions de l'app (client_id)

---

**Créé le** : 2025-11-08  
**Version** : 1.0  
**Auteur** : DQ System
