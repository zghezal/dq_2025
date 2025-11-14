# Lire le fichier
with open('src/callbacks/channels_drop.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ajouter dcc.Upload dans _render_file_input_row
old_input = '''            dcc.Input(
                id={'type': 'file-path-input', 'file_id': spec.file_id},
                placeholder=f\"Chemin ou URL vers {spec.name} (.{spec.format.value})\",
                className=\"form-control mb-2\"
            ),'''

new_input = '''            html.Div([
                dcc.Input(
                    id={'type': 'file-path-input', 'file_id': spec.file_id},
                    placeholder=f\"Chemin ou URL vers {spec.name} (.{spec.format.value})\",
                    className=\"form-control\",
                    style={\"marginBottom\": \"10px\"}
                ),
                dcc.Upload(
                    id={'type': 'file-upload', 'file_id': spec.file_id},
                    children=html.Button([
                        html.I(className=\"bi bi-folder2-open me-2\"),
                        \" Parcourir...\"
                    ], className=\"btn btn-outline-primary btn-sm\"),
                    style={\"display\": \"inline-block\"},
                    multiple=False
                )
            ]),'''

content = content.replace(old_input, new_input)

# Ajouter le callback d upload avant close_success_modal
upload_callback = ''''''

@callback(
    Output({'type': 'file-path-input', 'file_id': dash.dependencies.MATCH}, 'value'),
    Input({'type': 'file-upload', 'file_id': dash.dependencies.MATCH}, 'filename'),
    Input({'type': 'file-upload', 'file_id': dash.dependencies.MATCH}, 'contents'),
    State({'type': 'file-upload', 'file_id': dash.dependencies.MATCH}, 'id'),
    prevent_initial_call=True
)
def handle_file_upload(filename, contents, upload_id):
    \"\"\"Gère l upload de fichier et sauvegarde dans data/.\"\"\"
    if not filename or not contents:
        raise PreventUpdate
    
    import os
    import base64
    from pathlib import Path
    
    # Utiliser le dossier data/ pour sauvegarder les fichiers uploadés
    upload_dir = Path(\"data\")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Décoder le contenu base64
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Générer un nom de fichier avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_name, ext = os.path.splitext(filename)
        safe_filename = f\"{original_name}_{timestamp}{ext}\"
        file_path = upload_dir / safe_filename
        
        # Écrire le fichier
        with open(file_path, 'wb') as f:
            f.write(decoded)
        
        # Retourner le chemin absolu
        return str(file_path.absolute())
        
    except Exception as e:
        print(f\"Erreur lors de l upload: {e}\")
        return filename

''''''

# Insérer avant la dernière fonction
content = content.replace(
    '@callback(\n    Output(\'success-modal\', \'is_open\', allow_duplicate=True),',
    upload_callback + '@callback(\n    Output(\'success-modal\', \'is_open\', allow_duplicate=True),'
)

# Écrire le fichier modifié
with open('src/callbacks/channels_drop.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(' Fichier modifié avec succès!')
print(' Bouton Parcourir ajouté')
print(' Callback d upload ajouté')
