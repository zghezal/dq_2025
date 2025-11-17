# demo.py

from src.context.spark_context import SparkDQContext
from src.plugins.metrics.missing_rate import MissingRate
import pandas as pd

# Exemple 1 : Avec fichiers Parquet (natif Spark)
context = SparkDQContext(catalog={
    "customers": "data/customers.parquet"
})

plugin = MissingRate()
result = plugin.run(context, dataset="customers", column="email")
print(result.value)  # 0.02

# Exemple 2 : Avec Pandas DataFrame (converti automatiquement)
df_pandas = pd.DataFrame({
    'id': [1, 2, 3],
    'value': [10, None, 30]
})

context = SparkDQContext(catalog={
    "test_data": df_pandas  # Pandas → Spark automatiquement
})

result = plugin.run(context, dataset="test_data", column="value")
print(result.value)  # 0.333...

context.stop()
```

---

## ✅ Avantages de cette approche

### 1. **Un seul code par plugin**
```
✅ missing_rate.py (fonctionne partout)
❌ missing_rate_spark.py (duplication inutile)