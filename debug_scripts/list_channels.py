import json

with open('managed_folders/channels/channels.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total canaux: {len(data)}")
print("\nCanaux créés:")
for channel_id, channel_data in data.items():
    name = channel_data.get('name', 'N/A')
    nb_files = len(channel_data.get('file_specifications', []))
    is_public = channel_data.get('is_public', True)
    access = "Public" if is_public else "Privé"
    print(f"  - {name} ({access}, {nb_files} fichier(s))")
