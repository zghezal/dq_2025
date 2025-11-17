import re

# Lire le fichier original
with open('src/callbacks/channels_drop.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver et remplacer la section _render_file_input_row
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Détecter le début de dcc.Input dans _render_file_input_row
    if 'dcc.Input(' in line and "'file-path-input'" in line:
        # Garder jusqu'à la ligne actuelle
        new_lines.append(line)
        
        # Ajouter les lignes suivantes jusqu'à la fermeture
        i += 1
        while i < len(lines) and not ('),''' in lines[i] or '),' in lines[i] and 'className' in lines[i-1]):
            new_lines.append(lines[i])
            i += 1
        
        # Ajouter la ligne de fermeture de dcc.Input mais la modifier
        if i < len(lines):
            # Remplacer la fermeture du dcc.Input par un html.Div englobant
            new_lines[-1] = new_lines[-1].replace('className="form-control mb-2"', 'className="form-control"')
            new_lines.append('            ),\n')
            new_lines.append('            dcc.Upload(\n')
            new_lines.append("                id={'type': 'file-upload', 'file_id': spec.file_id},\n")
            new_lines.append('                children=html.Button([\n')
            new_lines.append('                    html.I(className="bi bi-folder2-open me-2"),\n')
            new_lines.append('                    " Parcourir..."\n')
            new_lines.append('                ], className="btn btn-outline-primary btn-sm"),\n')
            new_lines.append('                multiple=False\n')
            new_lines.append('            )\n')
            new_lines.append('        ]),\n')
            i += 1
            continue
    
    new_lines.append(line)
    i += 1

# Écrire le fichier
with open('src/callbacks/channels_drop_NEW.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fichier src/callbacks/channels_drop_NEW.py créé")
