import pandas as pd
from src.core.models_inventory import LocalSource

class LocalReader:
    def __init__(self, alias_map):
        self.alias_map = alias_map

    def __call__(self, alias: str) -> pd.DataFrame:
        src = self.alias_map[alias]
        if isinstance(src, LocalSource):
            path = src.path
            if path.endswith('.csv'):
                return pd.read_csv(path)
            if path.endswith('.parquet'):
                return pd.read_parquet(path)
            raise ValueError(f"Unsupported local file: {path}")
        raise NotImplementedError("Only local source implemented in this build")
