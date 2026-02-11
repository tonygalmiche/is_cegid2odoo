# Transfert Azure CEGID → Odoo

Script de téléchargement automatique des fichiers exportés par Cegid Data Access depuis Azure Blob Storage.

## Prérequis

- Python 3.6+
- Accès au portail Cegid (Gestion des comptes)
- Accès au portail Cegid Developers

## Installation

```bash
mkdir /opt/transfert-azure-cegid
cd /opt/transfert-azure-cegid/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install azure-storage-blob requests
```

## Configuration

Copier le fichier d'exemple et le personnaliser :

```bash
cp config.py.sample config.py
```

### Mode de connexion

Le script supporte 2 modes de connexion, configurables via le paramètre `mode` dans `config.py` :

| Mode      | Description                                              | Durée de validité |
|-----------|----------------------------------------------------------|-------------------|
| `"api"`   | Génère automatiquement un SAS token via l'API Cegid      | Illimitée         |
| `"sas_url"` | Utilise une URL SAS statique (dépannage)               | 24 heures         |

### Mode `"api"` (recommandé)

Ce mode nécessite 4 paramètres dans `config.py` :

- `cegid_tenant_id` — votre numéro de compte client Cegid (ex: `98537347`)
- `cegid_api_key_id` — l'identifiant de votre clé d'API
- `cegid_api_key_secret` — le secret de votre clé d'API
- `cegid_subscription_key` — la clé d'abonnement au portail développeur

#### Étape 1 : Créer une clé d'API (portail Cegid Gestion des comptes)

1. Aller sur **[account.cegid.com](https://account.cegid.com)**
2. Se connecter avec votre compte Cegid
3. Dans le menu latéral gauche, cliquer sur **Clés d'API**
4. Cliquer sur **Créer une clé d'API**
5. Donner un nom à la clé (ex: `cegid-data-access-pour-odoo`)
6. Associer le service **Cegid Data Access (SAAS_DATA_ACCESS)**
7. Valider la création
8. **IMPORTANT** : noter immédiatement le **Secret** affiché — il n'est montré qu'une seule fois !
9. Noter également l'**ID** de la clé (affiché en bleu sous le nom)

→ L'**ID** correspond à `cegid_api_key_id` dans `config.py`
→ Le **Secret** correspond à `cegid_api_key_secret` dans `config.py`

#### Étape 2 : Obtenir la clé d'abonnement (portail Cegid Developers)

1. Aller sur **[developers.cegid.com](https://developers.cegid.com)**
2. Cliquer sur l'icône profil en haut à droite, puis **Log in**
3. Se connecter avec le même compte Cegid
4. Une fois connecté, cliquer sur **Subscriptions** dans la barre de navigation en haut
5. Vous verrez une ligne pour le produit **Cegid Data Access** avec votre Customer Id
6. Si les clés n'existent pas encore, cliquer sur **"Create primary and secondary keys"**
7. Cliquer sur **Show** à côté de **Primary key** pour révéler la clé
8. Copier la **Primary key**

→ Cette clé correspond à `cegid_subscription_key` dans `config.py`

### Mode `"sas_url"` (dépannage)

Ce mode utilise une URL SAS générée manuellement depuis le portail Cegid. L'URL est valide **24 heures** seulement.

Pour obtenir une URL SAS :

1. Se connecter sur le portail Cegid
2. Générer une URL SAS pour le conteneur Azure Blob Storage
3. Coller l'URL dans le paramètre `sas_url` de `config.py`

## Exécution du transfert

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/transfert-azure-cegid.py
```

Le script :
1. Se connecte au conteneur Azure (via API ou SAS URL selon le mode)
2. Liste tous les fichiers disponibles
3. Télécharge chaque fichier dans le dossier de destination (`dossier_de_destintion`)
4. Supprime chaque fichier du conteneur Azure après téléchargement

## Gestion des requêtes planifiées (cegid-requetes.py)

Ce script permet de consulter et piloter les requêtes planifiées dans Cegid Data Access,
notamment pour **forcer une exécution immédiate** sans attendre la planification de nuit.

### Configuration préalable : découvrir le Provider ID

Le Provider ID (GUID) identifie le fournisseur de données (ex: "Cegid XRP / HR Sprint On Demand").
Il doit être renseigné dans `config.py` :

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/cegid-requetes.py --discover
```

Le script tente de découvrir automatiquement le Provider ID. Une fois trouvé, le copier dans `config.py` :

```python
cegid_provider_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Lister les requêtes planifiées

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/cegid-requetes.py --list
```

Affiche toutes les requêtes avec leur nom, état, cron, et dates d'exécution.

### Forcer l'exécution

Reprogrammer la prochaine exécution de toutes les requêtes dans les 15 prochaines minutes :

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/cegid-requetes.py --force
```

Forcer une seule requête par nom (recherche partielle) :

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/cegid-requetes.py --force --name ECRITURE
```

Forcer à une heure précise (UTC) :

```bash
/opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/cegid-requetes.py --force --time 14:30
```

> **Note** : seul le champ `nextExecution` est modifié. Le **cron** (planification quotidienne)
> reste inchangé et reprend normalement après l'exécution forcée.

On peut aussi définir une heure par défaut dans `config.py` :

```python
cegid_force_time = "06:00"  # Forcer à 06:00 UTC par défaut
```

## Exécution automatique (cron)

Pour exécuter le script de transfert toutes les heures :

```bash
crontab -e
```

Ajouter la ligne :

```
0 * * * * /opt/transfert-azure-cegid/venv/bin/python /opt/addons/is_cegid2odoo/script-externe/transfert-azure-cegid.py >> /var/log/transfert-azure-cegid.log 2>&1
```
