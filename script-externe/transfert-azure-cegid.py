import os
from azure.storage.blob import BlobServiceClient, ContainerClient
from config import sas_url, dossier_de_destintion


#** Mise en place de l’environnent python pour ce script **********************
# mkdir /opt/transfert-azure-cegid
# cd /opt/transfert-azure-cegid/
# python3 -m venv venv
# source venv/bin/activate
# pip install --upgrade pip
# pip install azure-storage-blob
# /opt/transfert-azure-cegid/venv/bin/python  /opt/addons/is_cegid2odoo/script-externe/transfert-azure-cegid.py 


# Créer un client pour le conteneur
container_client = ContainerClient.from_container_url(sas_url)

# Récupérer tous les fichiers
blobs = list(container_client.list_blobs())

# Afficher l'en-tête
print(f"{'Nom du fichier':<80} {'Taille': >12} {'Date modification':<25}")
print("=" * 120)

# Afficher chaque fichier sur une ligne
for blob in blobs:
    # Formater la taille
    if blob.size < 1024:
        size_str = f"{blob.size} B"
    elif blob.size < 1024*1024:
        size_str = f"{blob.size/1024:.2f} KB"
    else: 
        size_str = f"{blob.size/(1024*1024):.2f} MB"
    
    # Formater la date
    date_str = blob.last_modified.strftime("%Y-%m-%d %H:%M:%S")
    
    # Afficher la ligne
    print(f"{blob.name:<80} {size_str: >12} {date_str: <25}")

print("=" * 120)
print(f"Total : {len(blobs)} fichier(s)")

# Créer le dossier de destination s'il n'existe pas
os.makedirs(dossier_de_destintion, exist_ok=True)

# Télécharger chaque fichier
print("\nTéléchargement des fichiers...")
print("-" * 120)

for blob in blobs:
    # Extraire uniquement le nom du fichier (sans les sous-dossiers)
    filename = os.path.basename(blob.name)
    destination_path = os.path.join(dossier_de_destintion, filename)
    
    # Télécharger le blob
    print(f"Téléchargement de {blob.name}...", end=" ")
    blob_client = container_client.get_blob_client(blob.name)
    
    with open(destination_path, "wb") as file:
        download_stream = blob_client.download_blob()
        file.write(download_stream.readall())
    
    # Supprimer le fichier d'origine sur Azure
    blob_client.delete_blob()
    print("OK (supprimé de Azure)")

print("-" * 120)
print(f"Téléchargement terminé ! {len(blobs)} fichier(s) téléchargé(s) dans {dossier_de_destintion}")
