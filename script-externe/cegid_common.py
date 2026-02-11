"""
Module commun pour les scripts Cegid Data Access.
Fournit l'authentification et les fonctions utilitaires partagées.
"""

import sys
import requests
from config import (
    cegid_api_base_url,
    cegid_tenant_id,
    cegid_api_key_id,
    cegid_api_key_secret,
    cegid_subscription_key,
)


def get_cegid_token():
    """Obtenir un jeton d'autorisation via l'API Cegid Data Access."""
    url = f"{cegid_api_base_url}/tokenprovider/Token"
    params = {"api-key-Id": cegid_api_key_id}
    headers = {
        "x-tenantId": cegid_tenant_id,
        "api-key-secret": cegid_api_key_secret,
        "Ocp-Apim-Subscription-Key": cegid_subscription_key,
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        print(f"ERREUR: Impossible d'obtenir le token Cegid (HTTP {response.status_code})")
        print(f"Réponse : {response.text}")
        sys.exit(1)
    data = response.json()
    return data["accessToken"]


def get_auth_headers(token):
    """Construire les headers d'authentification pour les appels API."""
    return {
        "x-tenantId": cegid_tenant_id,
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": cegid_subscription_key,
        "Content-Type": "application/json",
    }


def get_sas_url_from_api():
    """Obtenir une URL SAS fraîche via l'API Cegid Data Access."""
    token = get_cegid_token()
    headers = get_auth_headers(token)
    url = f"{cegid_api_base_url}/storage/api/V1/storages/GetSASTokenLRD"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"ERREUR: Impossible d'obtenir le SAS token (HTTP {response.status_code})")
        print(f"Réponse : {response.text}")
        sys.exit(1)
    data = response.json()
    container_url = f"{data['blobServiceUri']}{data['containerName']}{data['sasToken']}"
    print(f"SAS URL générée automatiquement via l'API Cegid (valide ~1h)")
    return container_url
