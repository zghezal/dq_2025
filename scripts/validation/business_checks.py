import pandas as pd
from datetime import datetime

def run(context, params):
    dataset_alias = params.get('dataset', 'sales_upload')
    min_amount = params.get('min_amount', 0.01)
    max_amount = params.get('max_amount', 1000000)
    
    try:
        df = context.load(dataset_alias)
    except Exception as e:
        return {
            'script_id': 'business_validation',
            'status': 'error',
            'metrics': {},
            'tests': {},
            'error_message': f'Erreur: {e}'
        }
    
    if len(df) == 0:
        return {
            'script_id': 'business_validation',
            'status': 'error',
            'metrics': {},
            'tests': {},
            'error_message': 'Dataset vide'
        }
    
    # Métriques
    negative_amounts = df[df['amount'] < 0] if 'amount' in df.columns else pd.DataFrame()
    negative_count = len(negative_amounts)
    
    out_of_range = df[(df['amount'] < min_amount) | (df['amount'] > max_amount)] if 'amount' in df.columns else pd.DataFrame()
    out_of_range_count = len(out_of_range)
    
    duplicate_ids = df['transaction_id'].duplicated().sum() if 'transaction_id' in df.columns else 0
    
    metrics = {
        'negative_amounts_count': negative_count,
        'out_of_range_count': out_of_range_count,
        'duplicate_ids_count': int(duplicate_ids),
        'total_rows': len(df)
    }
    
    # Tests
    tests = {
        'no_negative_amounts': {
            'status': 'passed' if negative_count == 0 else 'failed',
            'value': negative_count,
            'threshold': 0,
            'message': f'{negative_count} montant(s) négatif(s)'
        },
        'amounts_in_range': {
            'status': 'passed' if out_of_range_count == 0 else 'failed',
            'value': out_of_range_count,
            'threshold': 0,
            'message': f'{out_of_range_count} montant(s) hors plage'
        },
        'no_duplicate_ids': {
            'status': 'passed' if duplicate_ids == 0 else 'failed',
            'value': int(duplicate_ids),
            'threshold': 0,
            'message': f'{duplicate_ids} ID en double'
        }
    }
    
    all_tests_passed = all(t['status'] == 'passed' for t in tests.values())
    
    return {
        'script_id': 'business_validation',
        'status': 'success' if all_tests_passed else 'failed',
        'metrics': metrics,
        'tests': tests,
        'investigations': []
    }

if __name__ == '__main__':
    class MockContext:
        def load(self, alias):
            return pd.DataFrame({
                'transaction_id': ['T001', 'T002', 'T003', 'T004', 'T002'],
                'amount': [100.50, -50.00, 1500000, 250.75, 100.00],
                'customer_id': ['C001', 'C002', 'C003', 'C004', 'C005'],
                'date': ['2025-11-01', '2025/11/02', '2025-11-03', '2025-11-04', '2025-11-05']
            })
    
    result = run(MockContext(), {'dataset': 'test', 'min_amount': 0.01, 'max_amount': 1000000})
    print('=' * 60)
    print(f"Status: {result['status']}")
    print('Métriques:')
    for k, v in result['metrics'].items():
        print(f'  - {k}: {v}')
    print('Tests:')
    for tid, tdata in result['tests'].items():
        icon = '' if tdata['status'] == 'passed' else ''
        print(f'  {icon} {tid}: {tdata["message"]}')
    print('=' * 60)
