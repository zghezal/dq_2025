import pandas as pd

def run(context, params):
    dataset_alias = params.get('dataset', 'sales_2024')
    min_threshold = params.get('min_threshold', 0.95)
    
    try:
        df = context.load(dataset_alias)
    except Exception as e:
        return {
            'script_id': 'sample_analysis',
            'status': 'error',
            'metrics': {},
            'tests': {},
            'error_message': f'Impossible de charger: {e}'
        }
    
    if len(df) > 0:
        completion_rates = []
        for col in df.columns:
            completion_rate = 1 - (df[col].isna().sum() / len(df))
            completion_rates.append(completion_rate)
        avg_completion_rate = sum(completion_rates) / len(completion_rates)
    else:
        avg_completion_rate = 0.0
    
    numeric_cols_count = len(df.select_dtypes(include=['number']).columns)
    shape_ratio = len(df) / len(df.columns) if len(df.columns) > 0 else 0
    
    metrics = {
        'avg_completion_rate': round(avg_completion_rate, 4),
        'numeric_columns_count': numeric_cols_count,
        'shape_ratio': round(shape_ratio, 2),
        'total_rows': len(df),
        'total_columns': len(df.columns)
    }
    
    tests = {}
    
    completion_status = 'passed' if avg_completion_rate >= min_threshold else 'failed'
    tests['min_completion_check'] = {
        'status': completion_status,
        'value': avg_completion_rate,
        'threshold': min_threshold,
        'message': f'Taux complétion: {avg_completion_rate:.2%}'
    }
    
    numeric_status = 'passed' if numeric_cols_count > 0 else 'failed'
    tests['numeric_columns_presence'] = {
        'status': numeric_status,
        'value': numeric_cols_count,
        'threshold': 1,
        'message': f'{numeric_cols_count} colonnes numériques'
    }
    
    empty_status = 'passed' if len(df) > 0 else 'failed'
    tests['non_empty_dataset'] = {
        'status': empty_status,
        'value': len(df),
        'threshold': 1,
        'message': f'Dataset: {len(df)} lignes'
    }
    
    all_tests_passed = all(t['status'] == 'passed' for t in tests.values())
    status = 'success' if all_tests_passed else 'failed'
    
    return {
        'script_id': 'sample_analysis',
        'status': status,
        'metrics': metrics,
        'tests': tests,
        'investigations': []
    }

if __name__ == '__main__':
    class MockContext:
        def load(self, alias):
            return pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'name': ['Alice', 'Bob', None, 'David', 'Eve'],
                'value': [10.5, 20.3, 30.1, None, 50.9],
                'category': ['A', 'B', 'A', 'C', None]
            })
    
    result = run(MockContext(), {'dataset': 'test', 'min_threshold': 0.80})
    print('=' * 60)
    print('RÉSULTAT DU SCRIPT')
    print('=' * 60)
    print(f"Script ID: {result['script_id']}")
    print(f"Status: {result['status']}")
    print(f"Métriques: {len(result['metrics'])}")
    for k, v in result['metrics'].items():
        print(f'  - {k}: {v}')
    print(f"Tests: {len(result['tests'])}")
    for tid, tdata in result['tests'].items():
        icon = '' if tdata['status'] == 'passed' else ''
        print(f'  {icon} {tid}: {tdata["message"]}')
