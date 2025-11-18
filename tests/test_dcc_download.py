"""
Test minimal pour vérifier si dcc.Download fonctionne.
"""

from dash import Dash, html, dcc, callback, Output, Input, ctx
import dash_bootstrap_components as dbc
from pathlib import Path

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1("Test dcc.Download"),
    html.Hr(),
    
    dbc.Button("Télécharger Fichier Test", id="test-download-btn", color="primary"),
    
    dcc.Download(id="test-download"),
    
    html.Div(id="test-output", className="mt-3")
], className="py-4")


@callback(
    Output("test-download", "data"),
    Input("test-download-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_test(n_clicks):
    """Télécharge un fichier de test."""
    if n_clicks:
        # Trouver un fichier Excel existant
        test_file = Path("reports/channel_submissions").glob("*.xlsx")
        test_file = list(test_file)
        
        if test_file:
            file_path = test_file[0]
            print(f"[TEST] Téléchargement de: {file_path}")
            print(f"[TEST] Taille: {file_path.stat().st_size} octets")
            
            result = dcc.send_file(str(file_path))
            print(f"[TEST] dcc.send_file retourné: {type(result)}")
            print(f"[TEST] Clés du dict: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            return result
        else:
            print("[TEST] Aucun fichier trouvé!")
    
    from dash.exceptions import PreventUpdate
    raise PreventUpdate


@callback(
    Output("test-output", "children"),
    Input("test-download-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_message(n_clicks):
    """Affiche un message après le clic."""
    if n_clicks:
        return dbc.Alert(f"Téléchargement déclenché ! (clic #{n_clicks})", color="success")
    
    from dash.exceptions import PreventUpdate
    raise PreventUpdate


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DCC.DOWNLOAD")
    print("=" * 60)
    print()
    print("Ouvrez http://127.0.0.1:8051")
    print("Cliquez sur le bouton et vérifiez:")
    print("  1. Le fichier se télécharge dans votre dossier Téléchargements")
    print("  2. Un message vert apparaît")
    print("  3. Aucune erreur dans la console du navigateur")
    print()
    print("=" * 60)
    
    app.run(debug=True, port=8051)
