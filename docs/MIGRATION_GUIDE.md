# 🔄 Guide de Migration - Sources de Données Multiples

## Pour les Utilisateurs Existants

Si vous avez déjà des canaux configurés, voici comment migrer vers le nouveau système multi-sources.

---

## Changements

### Avant (Système Ancien)

```python
FileSpecification(
    file_id='sales',
    name='Fichier des ventes',
    format=FileFormat.CSV
)
# ➡️ Upload manuel uniquement via l'interface
```

### Après (Système Nouveau)

```python
FileSpecification(
    file_id='sales',
    name='Fichier des ventes',
    format=FileFormat.CSV,
    source_type=DataSourceType.LOCAL,  # ✅ Explicite
    connection_params={}                # ✅ Vide pour upload manuel
)
```

---

## Rétrocompatibilité

✅ **Tous les canaux existants continuent de fonctionner** sans modification !

Le champ `source_type` a une valeur par défaut :

```python
source_type: DataSourceType = DataSourceType.LOCAL  # Par défaut
```

Les anciens canaux seront automatiquement traités comme des uploads locaux.

---

## Migration Manuelle (Optionnel)

### Étape 1 : Identifier les Canaux

```python
from src.core.channel_manager import ChannelManager

manager = ChannelManager()
channels = manager.list_channels()

for channel in channels:
    print(f"Canal: {channel.name}")
    for spec in channel.file_specifications:
        print(f"  - {spec.name}: {spec.source_type}")
```

### Étape 2 : Mettre à Jour un Canal

#### Exemple : Passer d'Upload Local à SharePoint

```python
# Charger le canal existant
channel = manager.get_channel('my_channel_id')

# Trouver la spec à modifier
spec = next(s for s in channel.file_specifications if s.file_id == 'sales')

# Changer pour SharePoint
spec.source_type = DataSourceType.SHAREPOINT
spec.connection_params = {
    'site_url': 'https://company.sharepoint.com/sites/data',
    'folder_path': '/Shared Documents/Sales',
    'file_name': 'sales_monthly.xlsx',
    'access_token': os.environ['SP_TOKEN'],
    'format': 'xlsx'
}

# Sauvegarder
manager.update_channel(channel)
```

#### Exemple : Ajouter une Source Dataiku en Complément

```python
# Ajouter une nouvelle spec Dataiku
from src.core.models_channels import FileSpecification, DataSourceType, FileFormat

new_spec = FileSpecification(
    file_id='history_dku',
    name='Historique (Dataiku)',
    source_type=DataSourceType.DATAIKU_DATASET,
    format=FileFormat.CSV,
    required=False,
    connection_params={
        'project_key': 'SALES',
        'dataset_name': 'sales_history',
        'sampling': 'head',
        'limit': 50000
    }
)

channel.file_specifications.append(new_spec)
manager.update_channel(channel)
```

---

## Scénarios de Migration Courants

### Scénario 1 : Automatiser avec HUE

**Avant** : L'équipe uploadait manuellement un fichier extrait depuis Hive.

**Après** : Configuration directe vers HUE.

```python
spec.source_type = DataSourceType.HUE
spec.connection_params = {
    'hue_url': 'http://hue.company.com:8888',
    'auth_token': os.environ['HUE_TOKEN'],
    'query': 'SELECT * FROM sales WHERE date >= current_date - 30',
    'database': 'production'
}
```

**Avantage** : Données toujours à jour, pas besoin d'extraction manuelle.

---

### Scénario 2 : Centraliser sur SharePoint

**Avant** : Chaque équipe uploadait via l'interface web.

**Après** : Les équipes déposent sur SharePoint, le système récupère automatiquement.

```python
spec.source_type = DataSourceType.SHAREPOINT
spec.connection_params = {
    'site_url': 'https://company.sharepoint.com/sites/dq',
    'folder_path': '/Shared Documents/TeamA/Deposits',
    'file_name': 'data_monthly.xlsx',
    'client_id': os.environ['SP_CLIENT_ID'],
    'client_secret': os.environ['SP_CLIENT_SECRET'],
    'format': 'xlsx'
}
```

**Avantage** : Les équipes utilisent SharePoint (déjà connu), le DQ est automatique.

---

### Scénario 3 : Réutiliser des Datasets Dataiku

**Avant** : Export manuel depuis Dataiku → Upload sur DQ.

**Après** : Référence directe au dataset.

```python
spec.source_type = DataSourceType.DATAIKU_DATASET
spec.connection_params = {
    'project_key': 'PREP_SALES',
    'dataset_name': 'sales_prepared',
    'sampling': 'full'
}
```

**Avantage** : Pas d'export/import, données synchronisées.

---

## Script de Migration Complet

```python
"""
Migration des canaux vers sources multiples
Convertit les uploads locaux en sources SharePoint/HUE/Dataiku
"""

import os
from src.core.channel_manager import ChannelManager
from src.core.models_channels import DataSourceType

# Configuration de migration
MIGRATIONS = {
    'sales_channel': {
        'file_id': 'sales',
        'new_source': DataSourceType.SHAREPOINT,
        'params': {
            'site_url': 'https://company.sharepoint.com/sites/sales',
            'folder_path': '/Shared Documents/DQ',
            'file_name': 'sales_latest.xlsx',
            'access_token': os.environ['SP_TOKEN'],
            'format': 'xlsx'
        }
    },
    'inventory_channel': {
        'file_id': 'inventory',
        'new_source': DataSourceType.DATAIKU_DATASET,
        'params': {
            'project_key': 'INVENTORY',
            'dataset_name': 'inventory_master',
            'sampling': 'full'
        }
    }
}

def migrate_channels():
    manager = ChannelManager()
    
    for channel_id, config in MIGRATIONS.items():
        print(f"\n🔄 Migration du canal: {channel_id}")
        
        # Charger le canal
        channel = manager.get_channel(channel_id)
        if not channel:
            print(f"  ❌ Canal introuvable: {channel_id}")
            continue
        
        # Trouver la spec à migrer
        spec = next((s for s in channel.file_specifications 
                    if s.file_id == config['file_id']), None)
        
        if not spec:
            print(f"  ❌ FileSpec introuvable: {config['file_id']}")
            continue
        
        # Backup de l'ancienne config
        print(f"  📋 Ancien: {spec.source_type.value}")
        
        # Appliquer la migration
        spec.source_type = config['new_source']
        spec.connection_params = config['params']
        
        print(f"  ✅ Nouveau: {spec.source_type.value}")
        
        # Sauvegarder
        manager.update_channel(channel)
        print(f"  💾 Canal sauvegardé")
    
    print("\n✅ Migration terminée !")

if __name__ == '__main__':
    migrate_channels()
```

---

## Vérification Post-Migration

### Test de Connexion

```python
from src.connectors.factory import ConnectorFactory

# Pour chaque spec migrée
spec = channel.file_specifications[0]

connector = ConnectorFactory.create_connector(
    spec.source_type,
    spec.connection_params
)

success, message = connector.test_connection()
if success:
    print(f"✅ {spec.name}: {message}")
else:
    print(f"❌ {spec.name}: {message}")
```

### Test de Chargement

```python
# Charger un échantillon
df = connector.fetch_data()
print(f"✅ {len(df)} lignes chargées")
print(f"Colonnes: {list(df.columns)}")
```

---

## Rollback (Retour Arrière)

Si besoin de revenir à l'ancien système :

```python
# Revenir à LOCAL
spec.source_type = DataSourceType.LOCAL
spec.connection_params = {}

manager.update_channel(channel)
```

**Note** : Les fichiers uploadés manuellement avant la migration sont toujours disponibles.

---

## Support

Pour toute question sur la migration :

1. Consulter `DATA_SOURCES_DOC.md` pour la doc complète
2. Exécuter `demo_data_sources.py` pour tester les connecteurs
3. Contacter l'équipe DQ pour assistance

---

**Date de Migration** : 2025-11-08  
**Version** : 1.0
