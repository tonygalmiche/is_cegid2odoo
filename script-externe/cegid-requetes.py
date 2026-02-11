#!/usr/bin/env python3
"""
Script de gestion des requêtes planifiées Cegid Data Access.

Usage :
    python cegid-requetes.py --discover          Découvrir le provider ID
    python cegid-requetes.py --list              Lister les requêtes planifiées
    python cegid-requetes.py --force             Forcer l'exécution de toutes les requêtes
    python cegid-requetes.py --force --name NOM  Forcer une requête spécifique par nom
    python cegid-requetes.py --force --time 14:30  Forcer à une heure précise
"""

import sys
import argparse
import requests
from datetime import datetime, timedelta, timezone
from config import (
    cegid_api_base_url,
    cegid_tenant_id,
    cegid_provider_id,
    cegid_force_time,
)
from cegid_common import get_cegid_token, get_auth_headers


def discover_provider_id(token):
    """
    Tenter de découvrir le provider ID en testant plusieurs endpoints et IDs.
    """
    headers = get_auth_headers(token)

    # Liste élargie de provider IDs connus pour Cegid XRP / HR Sprint
    known_providers = [
        cegid_tenant_id,
        "cegid-xrp",
        "HR Sprint On Demand",
        "xrp",
        "hr-sprint",
        "cegid-hr",
        "paie",
    ]

    print("Tentative de découverte du provider ID...")
    print("=" * 80)

    # Méthode 1 : via l'endpoint datasources
    print("\n--- Méthode 1 : recherche via les datasources ---")
    for pid in known_providers:
        url = f"{cegid_api_base_url}/datasource/api/V2/datasources/tenant/{pid}"
        response = requests.get(url, headers=headers)
        print(f"  Test '{pid}' => HTTP {response.status_code}", end="")
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                print(f" => {len(data['data'])} datasource(s) trouvée(s) !")
                for ds in data["data"]:
                    real_pid = ds.get("providerId", pid)
                    print(f"    - {ds.get('name', '?')} (providerId: {real_pid})")
                final_pid = data["data"][0].get("providerId", pid)
                print(f"\n=> Ajoutez dans config.py :")
                print(f'   cegid_provider_id = "{final_pid}"')
                return final_pid
            else:
                print(" (réponse vide)")
        else:
            try:
                print(f" : {response.json().get('errorMessage', response.text[:100])}")
            except Exception:
                print(f" : {response.text[:100]}")

    # Méthode 2 : via l'endpoint collections
    print("\n--- Méthode 2 : recherche via les collections ---")
    for pid in known_providers:
        url = f"{cegid_api_base_url}/datasource/api/V1/foldersCollections/tenant/{pid}"
        response = requests.get(url, headers=headers)
        print(f"  Test '{pid}' => HTTP {response.status_code}", end="")
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f" => {len(data)} collection(s) trouvée(s) !")
                for col in data:
                    real_pid = col.get("providerId", pid)
                    print(f"    - {col.get('name', '?')} (providerId: {real_pid})")
                final_pid = data[0].get("providerId", pid)
                print(f"\n=> Ajoutez dans config.py :")
                print(f'   cegid_provider_id = "{final_pid}"')
                return final_pid
            else:
                print(" (réponse vide)")
        else:
            try:
                print(f" : {response.json().get('errorMessage', response.text[:100])}")
            except Exception:
                print(f" : {response.text[:100]}")

    # Méthode 3 : via l'endpoint schedulers
    print("\n--- Méthode 3 : recherche via les requêtes planifiées ---")
    for pid in known_providers:
        url = f"{cegid_api_base_url}/query/api/V1/schedulers/tenant/provider/{pid}"
        response = requests.get(url, headers=headers)
        print(f"  Test '{pid}' => HTTP {response.status_code}", end="")
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f" => {len(data)} requête(s) trouvée(s) !")
                for q in data:
                    name = q.get("query", {}).get("name", q.get("name", "?"))
                    print(f"    - {name}")
                print(f"\n=> Le provider ID est probablement : {pid}")
                print(f"   Ajoutez dans config.py :")
                print(f'   cegid_provider_id = "{pid}"')
                return pid
            else:
                print(" (réponse vide)")
        else:
            try:
                print(f" : {response.json().get('errorMessage', response.text[:100])}")
            except Exception:
                print(f" : {response.text[:100]}")

    # Si rien trouvé
    print("\n" + "=" * 80)
    print("Aucun provider ID trouvé automatiquement.")
    print()
    print("Pour le trouver manuellement :")
    print("1. Allez sur le portail Cegid Data Access (https://data-access.cegid.com)")
    print("2. Observez l'URL dans la barre d'adresse du navigateur")
    print("   Le provider ID (GUID) apparaît souvent dans l'URL")
    print("3. Ou inspectez les requêtes réseau (F12 > Network) lors du")
    print("   chargement de la page 'Requêtes enregistrées'")
    print("4. Cherchez un GUID de type : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    return None


def _format_date(date_str):
    """Formater une date ISO en format court YYYY-MM-DD HH:MM."""
    if not date_str or date_str == "?":
        return "?"
    try:
        # Supprimer les fractions de secondes (.1234567) avant le fuseau horaire
        import re
        clean = re.sub(r'\.\d+', '', date_str)
        dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return date_str


def list_queries(token, provider_id, show_sql=False):
    """Lister les requêtes planifiées."""
    headers = get_auth_headers(token)
    url = f"{cegid_api_base_url}/query/api/V1/schedulers/tenant/provider/{provider_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERREUR: Impossible de récupérer les requêtes (HTTP {response.status_code})")
        print(f"Réponse : {response.text}")
        sys.exit(1)

    queries = response.json()

    if not queries:
        print("Aucune requête planifiée trouvée.")
        return []

    print(f"{'#':<4} {'':3} {'Nom':<25} {'Cron':<18} {'Prochaine exécution':<22} {'Dernière exécution':<22} {'ID scheduler'}")
    print("=" * 140)

    for i, q in enumerate(queries, 1):
        name = q.get("query", {}).get("name", q.get("name", "?"))
        icon = "✅" if q.get("enable") else "❌"
        cron = q.get("cron", "?")
        next_exec = q.get("nextExecution", "?")
        last_exec = q.get("lastExecution", "?")
        scheduler_id = q.get("id", "?")
        sql = q.get("query", {}).get("content", "")

        # Formater les dates en format court
        next_exec = _format_date(next_exec)
        last_exec = _format_date(last_exec)

        print(f"{i:<4} {icon}  {name:<25} {cron:<18} {next_exec:<22} {last_exec:<22} {scheduler_id}")
        if show_sql and sql:
            print(f"     SQL: {sql}")

    print("=" * 140)
    print(f"Total : {len(queries)} requête(s)  |  ✅ = activée  |  ❌ = désactivée")
    return queries


def compute_next_execution(force_time_str=None):
    """
    Calculer la prochaine date d'exécution.
    Si force_time_str est fourni (HH:MM), utilise cette heure aujourd'hui (ou demain si passée).
    Sinon, planifie dans les 15 prochaines minutes.
    """
    now = datetime.now(timezone.utc)

    if force_time_str:
        try:
            hours, minutes = map(int, force_time_str.split(":"))
            target = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        except (ValueError, AttributeError):
            print(f"ERREUR: Format d'heure invalide '{force_time_str}'. Utilisez HH:MM")
            sys.exit(1)
    else:
        # Arrondir au prochain quart d'heure
        minutes_to_add = 15 - (now.minute % 15)
        if minutes_to_add < 5:
            minutes_to_add += 15  # Au moins 5 minutes dans le futur
        target = now + timedelta(minutes=minutes_to_add)
        target = target.replace(second=0, microsecond=0)
        return target


def force_execution(token, provider_id, queries, name_filter=None, force_time_str=None):
    """
    Forcer l'exécution des requêtes en modifiant nextExecution.
    Le cron (planification quotidienne) reste inchangé.
    """
    headers = get_auth_headers(token)
    target_time = compute_next_execution(force_time_str)

    print(f"\nProchaine exécution forcée à : {target_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("-" * 120)

    count = 0
    for q in queries:
        query_name = q.get("query", {}).get("name", q.get("name", "?"))

        # Filtrer par nom si demandé
        if name_filter and name_filter.upper() not in query_name.upper():
            continue

        if not q.get("enable"):
            print(f"  {query_name:<40} => Ignorée (désactivée)")
            continue

        # Conserver le cron original, modifier uniquement nextExecution
        original_cron = q.get("cron", "")
        original_next = q.get("nextExecution", "")

        q["nextExecution"] = target_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # PUT pour mettre à jour
        url = f"{cegid_api_base_url}/query/api/V1/schedulers"
        response = requests.put(url, headers=headers, json=q)

        if response.status_code == 200:
            print(f"  {query_name:<40} => OK (était: {original_next})")
            count += 1
        else:
            print(f"  {query_name:<40} => ERREUR (HTTP {response.status_code})")
            print(f"    Réponse : {response.text}")

    print("-" * 120)
    if count > 0:
        print(f"{count} requête(s) reprogrammée(s) à {target_time.strftime('%H:%M')} UTC")
        print(f"Le cron de planification quotidienne n'a PAS été modifié.")
    else:
        if name_filter:
            print(f"Aucune requête trouvée contenant '{name_filter}'")
        else:
            print("Aucune requête à reprogrammer.")


def toggle_scheduler(token, provider_id, scheduler_id, enable=False):
    """Activer ou désactiver une planification par son ID."""
    headers = get_auth_headers(token)

    # Récupérer toutes les planifications pour trouver celle avec cet ID
    url = f"{cegid_api_base_url}/query/api/V1/schedulers/tenant/provider/{provider_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERREUR: Impossible de récupérer les requêtes (HTTP {response.status_code})")
        sys.exit(1)

    queries = response.json()
    target = None
    for q in queries:
        if q.get("id") == scheduler_id:
            target = q
            break

    if not target:
        print(f"ERREUR: Planification '{scheduler_id}' non trouvée")
        sys.exit(1)

    name = target.get("query", {}).get("name", target.get("name", "?"))
    action = "Activation" if enable else "Désactivation"

    target["enable"] = enable

    url = f"{cegid_api_base_url}/query/api/V1/schedulers"
    response = requests.put(url, headers=headers, json=target)

    if response.status_code == 200:
        etat = "activée" if enable else "désactivée"
        print(f"{action} OK : {name} (ID: {scheduler_id}) => {etat}")
    else:
        print(f"ERREUR: {action} échouée (HTTP {response.status_code})")
        print(f"Réponse : {response.text}")


def main():
    parser = argparse.ArgumentParser(
        description="Gestion des requêtes planifiées Cegid Data Access"
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Découvrir le provider ID"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Lister les requêtes planifiées"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Forcer l'exécution des requêtes"
    )
    parser.add_argument(
        "--disable", action="store_true",
        help="Désactiver une planification par son ID"
    )
    parser.add_argument(
        "--enable", action="store_true",
        help="Réactiver une planification par son ID"
    )
    parser.add_argument(
        "--id", type=str, default=None,
        help="ID du scheduler (GUID) pour --disable ou --enable"
    )
    parser.add_argument(
        "--sql", action="store_true",
        help="Afficher les requêtes SQL (avec --list)"
    )
    parser.add_argument(
        "--name", type=str, default=None,
        help="Filtrer par nom de requête (recherche partielle)"
    )
    parser.add_argument(
        "--time", type=str, default=None,
        help="Heure de forçage (HH:MM en UTC). Si omis, dans les 15 prochaines minutes"
    )

    args = parser.parse_args()

    if not any([args.discover, args.list, args.force, args.disable, args.enable]):
        parser.print_help()
        sys.exit(0)

    # Authentification
    print("Authentification Cegid Data Access...")
    token = get_cegid_token()
    print("Authentification OK")
    print("=" * 120)

    # Mode découverte
    if args.discover:
        discover_provider_id(token)
        return

    # Vérifier le provider ID
    provider_id = cegid_provider_id
    if not provider_id:
        print("ERREUR: cegid_provider_id non configuré dans config.py")
        print("Lancez d'abord : python cegid-requetes.py --discover")
        sys.exit(1)

    # Liste
    if args.list:
        list_queries(token, provider_id, show_sql=args.sql)
        return

    # Désactiver / Réactiver
    if args.disable or args.enable:
        if not args.id:
            print("ERREUR: --id <GUID> requis avec --disable ou --enable")
            print("Lancez d'abord : python cegid-requetes.py --list")
            sys.exit(1)
        toggle_scheduler(token, provider_id, args.id, enable=args.enable)
        return

    # Forçage
    if args.force:
        queries = list_queries(token, provider_id)
        if not queries:
            return
        force_time = args.time or cegid_force_time or None
        force_execution(token, provider_id, queries, args.name, force_time)


if __name__ == "__main__":
    main()
