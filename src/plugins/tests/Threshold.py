# src/plugins/tests/threshold.py

from src.plugins.base import TestPlugin

class ThresholdTest(TestPlugin):
    """Test de seuil min/max (fonctionne sur scalaires et DataFrames)"""
    
    @property
    def key(self) -> str:
        return "threshold"
    
    @property
    def name(self) -> str:
        return "Seuil min/max"
    
    def params_spec(self) -> list:
        return [
            {
                "name": "column",
                "type": "string",
                "required": True,
                "description": "Nom de la colonne/métrique à tester"
            },
            {
                "name": "min",
                "type": "number",
                "required": False,
                "description": "Valeur minimale (inclusive)"
            },
            {
                "name": "max",
                "type": "number",
                "required": False,
                "description": "Valeur maximale (inclusive)"
            }
        ]
    
    def execute(self, context, params: dict, metric_result):
        """
        Test sur résultat de métrique
        
        Args:
            metric_result: Résultat d'une métrique (dict ou DataFrame)
        """
        column = params["column"]
        min_value = params.get("min")
        max_value = params.get("max")
        
        # Cas 1 : Résultat scalaire (dict)
        if isinstance(metric_result, dict):
            value = metric_result[column]
            
            passed = True
            if min_value is not None and value < min_value:
                passed = False
            if max_value is not None and value > max_value:
                passed = False
            
            return {
                "passed": passed,
                "value": value,
                "threshold": f"{min_value} <= {column} <= {max_value}",
                "details": f"{column} = {value:.2f}"
            }
        
        # Cas 2 : Résultat DataFrame (pandas)
        elif hasattr(metric_result, 'columns'):  # DataFrame
            values = metric_result[column]
            
            violations = []
            if min_value is not None:
                violations.extend(values[values < min_value].tolist())
            if max_value is not None:
                violations.extend(values[values > max_value].tolist())
            
            passed = len(violations) == 0
            
            return {
                "passed": passed,
                "violations_count": len(violations),
                "violations": violations[:10],  # Limite à 10 exemples
                "threshold": f"{min_value} <= {column} <= {max_value}",
                "details": f"{len(violations)} violation(s) détectée(s)"
            }