"""
Script pour vérifier que tous les Outputs des callbacks correspondent à des composants existants.
"""

import re
from pathlib import Path

def extract_callbacks(file_path):
    """Extrait tous les callbacks d'un fichier."""
    content = file_path.read_text(encoding='utf-8')
    
    # Pattern pour trouver les @callback avec leurs Outputs
    pattern = r'@callback\s*\(\s*(?:Output|Input|\[)'
    matches = re.finditer(pattern, content, re.MULTILINE)
    
    callbacks = []
    for match in matches:
        start = match.start()
        # Trouver la fin de la déclaration du callback (avant def)
        end_pattern = content.find('\ndef ', start)
        if end_pattern == -1:
            continue
        
        callback_decl = content[start:end_pattern]
        
        # Extraire les Outputs
        output_pattern = r"Output\s*\(\s*['\"]([^'\"]+)['\"]|Output\s*\(\s*\{[^}]+\}"
        outputs = re.findall(output_pattern, callback_decl)
        
        if outputs:
            callbacks.append({
                'file': file_path.name,
                'declaration': callback_decl[:200] + '...',
                'outputs': outputs
            })
    
    return callbacks

def main():
    print("🔍 Vérification des callbacks et composants...\n")
    
    # Chercher tous les fichiers de callbacks
    callbacks_dir = Path('src/callbacks')
    callback_files = list(callbacks_dir.glob('*.py'))
    
    all_callbacks = []
    for file_path in callback_files:
        callbacks = extract_callbacks(file_path)
        all_callbacks.extend(callbacks)
    
    print(f"✅ Trouvé {len(all_callbacks)} callbacks\n")
    
    # Afficher les callbacks avec pattern-matching
    pattern_matching = []
    for cb in all_callbacks:
        if any('{' in str(out) for out in cb['outputs']):
            pattern_matching.append(cb)
    
    if pattern_matching:
        print(f"⚠️  {len(pattern_matching)} callbacks utilisent pattern-matching:\n")
        for cb in pattern_matching:
            print(f"  📁 {cb['file']}")
            print(f"     {cb['declaration'][:150]}...")
            print()
    
    # Vérifier les composants dans app.py
    print("\n🔍 Composants dans app.layout:")
    app_content = Path('app.py').read_text(encoding='utf-8')
    
    # Chercher les dcc.Download
    downloads = re.findall(r'dcc\.Download\s*\(\s*id\s*=\s*["\']([^"\']+)["\']', app_content)
    print(f"  ✅ dcc.Download: {downloads}")
    
    # Chercher les composants avec pattern-matching
    pattern_comps = re.findall(r'id\s*=\s*\{[^}]+\}', app_content)
    if pattern_comps:
        print(f"  ✅ Pattern-matching components: {len(pattern_comps)}")
        for comp in pattern_comps[:5]:
            print(f"     - {comp}")
    
    print("\n" + "="*60)
    print("DIAGNOSTIC:")
    print("="*60)
    print()
    print("Si vous voyez l'erreur 'Cannot read properties of undefined',")
    print("c'est qu'un callback essaie de mettre à jour un composant qui")
    print("n'existe pas dans le layout.")
    print()
    print("Solutions:")
    print("1. Vérifier que chaque Output correspond à un composant existant")
    print("2. Pour pattern-matching: vérifier que les composants sont créés dynamiquement")
    print("3. Utiliser prevent_initial_call=True pour éviter les mises à jour avant création")
    print()

if __name__ == '__main__':
    main()
