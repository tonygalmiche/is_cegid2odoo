# -*- coding: utf-8 -*-

import os
import csv
import logging
import time
from datetime import datetime
from subprocess import Popen, PIPE

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IsCegidImport(models.Model):
    _name = 'is.cegid.import'
    _description = 'Import CSV Cegid'

    # Mapping des colonnes CSV vers les modèles Odoo
    # Clé = tuple des colonnes triées, Valeur = nom du modèle
    MODEL_MAPPING = {
        # is.cegid.histocumsal
        ('PHC_CUMULPAIE', 'PHC_MONTANT', 'PHC_SALARIE'): {
            'model': 'is.cegid.histocumsal',
            'fields': {
                'PHC_SALARIE': 'phc_salarie',
                'PHC_CUMULPAIE': 'phc_cumulpaie',
                'PHC_MONTANT': 'phc_montant',
            }
        },
        # is.cegid.ecriture
        ('E_AUXILIAIRE', 'E_CREDIT', 'E_DATECOMPTABLE', 'E_DEBIT', 'E_GENERAL', 'E_LIBELLE', 'E_REFLIBRE', 'E_REFINTERNE'): {
            'model': 'is.cegid.ecriture',
            'fields': {
                'E_DATECOMPTABLE': 'e_datecomptable',
                'E_REFINTERNE': 'e_refinterne',
                'E_LIBELLE': 'e_libelle',
                'E_GENERAL': 'e_general',
                'E_DEBIT': 'e_debit',
                'E_CREDIT': 'e_credit',
                'E_AUXILIAIRE': 'e_auxiliaire',
                'E_REFLIBRE': 'e_reflibre',
            }
        },
        # is.cegid.absencesalarie
        ('PCN_DATEDEBUTABS', 'PCN_DATEFINABS', 'PCN_DEBUTDJ', 'PCN_FINDJ', 'PCN_GUID', 'PCN_HEURES', 'PCN_JOURS', 
         'PCN_LIBELLE', 'PCN_ORDRE', 'PCN_PERIODECP', 'PCN_SALARIE', 'PCN_SENSABS', 'PCN_TYPECONGE', 'PCN_TYPEMVT'): {
            'model': 'is.cegid.absencesalarie',
            'fields': {
                'PCN_TYPEMVT': 'pcn_typemvt',
                'PCN_SALARIE': 'pcn_salarie',
                'PCN_ORDRE': 'pcn_ordre',
                'PCN_PERIODECP': 'pcn_periodecp',
                'PCN_TYPECONGE': 'pcn_typeconge',
                'PCN_SENSABS': 'pcn_sensabs',
                'PCN_LIBELLE': 'pcn_libelle',
                'PCN_DATEDEBUTABS': 'pcn_datedebutabs',
                'PCN_DEBUTDJ': 'pcn_debutdj',
                'PCN_DATEFINABS': 'pcn_datefinabs',
                'PCN_FINDJ': 'pcn_findj',
                'PCN_JOURS': 'pcn_jours',
                'PCN_HEURES': 'pcn_heures',
                'PCN_GUID': 'pcn_guid',
            }
        },
        # is.cegid.analytiq
        ('Y_AXE', 'Y_CONTREPARTIEAUX', 'Y_CREDIT', 'Y_DATECOMPTABLE', 'Y_DEBIT', 'Y_GENERAL', 'Y_JOURNAL', 
         'Y_LIBELLE', 'Y_NATUREPIECE', 'Y_REFEXTERNE', 'Y_REFINTERNE', 'Y_SECTION'): {
            'model': 'is.cegid.analytiq',
            'fields': {
                'Y_DATECOMPTABLE': 'y_datecomptable',
                'Y_GENERAL': 'y_general',
                'Y_AXE': 'y_axe',
                'Y_SECTION': 'y_section',
                'Y_REFINTERNE': 'y_refinterne',
                'Y_LIBELLE': 'y_libelle',
                'Y_NATUREPIECE': 'y_naturepiece',
                'Y_REFEXTERNE': 'y_refexterne',
                'Y_JOURNAL': 'y_journal',
                'Y_CONTREPARTIEAUX': 'y_contrepartieaux',
                'Y_DEBIT': 'y_debit',
                'Y_CREDIT': 'y_credit',
            }
        },
    }

    def _detect_model_from_columns(self, columns):
        """
        Détecte le modèle Odoo correspondant aux colonnes du fichier CSV
        """
        columns_upper = tuple(sorted([col.upper().strip() for col in columns]))
        
        for mapping_columns, mapping_info in self.MODEL_MAPPING.items():
            # Vérifier si toutes les colonnes du mapping sont présentes dans le fichier
            if set(mapping_columns).issubset(set(columns_upper)):
                return mapping_info
            # Vérifier aussi l'inverse (colonnes du fichier sont un sous-ensemble)
            if set(columns_upper).issubset(set(mapping_columns)):
                return mapping_info
        
        return None

    def _convert_value(self, value, field_name, model_obj):
        """
        Convertit une valeur CSV vers le type approprié pour le champ Odoo
        """
        if not value or value.strip() == '':
            return False
        
        value = value.strip()
        # Supprimer les guillemets si présents
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        value = value.strip()
        
        field = model_obj._fields.get(field_name)
        if not field:
            return value
        
        if field.type == 'float':
            try:
                # Gérer les formats avec virgule ou point
                value = value.replace(',', '.')
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        elif field.type == 'integer':
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0
        elif field.type in ('datetime', 'date'):
            try:
                # Essayer différents formats de date
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',      # ISO: 2025-06-30 00:00:00
                    '%Y-%m-%d',                # ISO: 2025-06-30
                    '%m/%d/%Y %H:%M:%S',       # US: 06/30/2025 00:00:00
                    '%m/%d/%Y',                # US: 06/30/2025
                    '%d/%m/%Y %H:%M:%S',       # EU: 30/06/2025 00:00:00
                    '%d/%m/%Y',                # EU: 30/06/2025
                ]
                for fmt in date_formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                return False
            except Exception:
                return False
        else:
            return value

    def _transfert_azure_cegid(self):
        """
        Exécute le script de transfert des fichiers depuis Azure vers le dossier local
        Le script est configuré dans le modèle 'is.commande.externe' avec le nom 'transfert-azure-cegid'
        """
        name = 'transfert-azure-cegid'
        cdes = self.env['is.commande.externe'].search([('name', '=', name)])
        
        if not cdes:
            _logger.warning(f"Commande externe '{name}' non trouvée")
            return False
        
        _logger.info("Exécution du transfert Azure -> local...")
        
        for cde in cdes:
            cmd = cde.commande
            _logger.info(f"Exécution de la commande: {cmd}")
            
            try:
                p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                
                output = stdout.decode("utf-8").strip()
                if output:
                    _logger.info(f"Transfert Azure: {output}")
                
                if stderr:
                    error_msg = stderr.decode("utf-8").strip()
                    if error_msg:
                        _logger.error(f"Erreur transfert Azure: {error_msg}")
                        return False
                
            except Exception as e:
                _logger.error(f"Erreur lors de l'exécution du transfert Azure: {str(e)}")
                return False
        
        _logger.info("Transfert Azure terminé avec succès")
        return True

    def _import_csv_file(self, filepath):
        """
        Importe un fichier CSV dans le modèle Odoo correspondant
        Retourne un dict: {'success': bool, 'records': int, 'table': str, 'error': str}
        """
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        _logger.info(f"     Lecture du fichier: {filename} ({filesize} octets)")
        
        result = {'success': False, 'records': 0, 'table': '', 'error': ''}
        
        try:
            # Détecter l'encodage et le délimiteur
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                sample = f.read(1024)
                f.seek(0)
                
                # Détecter le délimiteur
                delimiter = ';' if ';' in sample else ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                columns = reader.fieldnames
                
                if not columns:
                    _logger.warning(f"     ERREUR: Aucune colonne trouvée dans le fichier {filename}")
                    result['error'] = "Aucune colonne trouvée"
                    return result
                
                _logger.info(f"     Colonnes détectées: {', '.join(columns)}")
                
                # Détecter le modèle
                mapping_info = self._detect_model_from_columns(columns)
                if not mapping_info:
                    _logger.warning(f"     ERREUR: Impossible de détecter le modèle Odoo pour ces colonnes")
                    _logger.warning(f"     Colonnes attendues: PHC_* (histocumsal), E_* (ecriture), PCN_* (absencesalarie), Y_* (analytiq)")
                    result['error'] = "Modèle Odoo non reconnu"
                    return result
                
                model_name = mapping_info['model']
                field_mapping = mapping_info['fields']
                
                _logger.info(f"     Modèle Odoo détecté: {model_name}")
                
                # Obtenir le modèle
                model_obj = self.env[model_name]
                
                # Vider la table (utiliser SQL pour plus de rapidité)
                self.env.cr.execute(f"SELECT COUNT(*) FROM {model_obj._table}")
                count_before = self.env.cr.fetchone()[0]
                self.env.cr.execute(f"DELETE FROM {model_obj._table}")
                _logger.info(f"     Table {model_obj._table} vidée ({count_before} enregistrements supprimés)")
                
                # Lire toutes les lignes
                rows = list(reader)
                
        except UnicodeDecodeError:
            # Essayer avec un autre encodage
            with open(filepath, 'r', encoding='latin-1') as f:
                delimiter = ';'
                reader = csv.DictReader(f, delimiter=delimiter)
                columns = reader.fieldnames
                
                mapping_info = self._detect_model_from_columns(columns)
                if not mapping_info:
                    _logger.warning(f"Fichier {filename}: Impossible de détecter le modèle pour les colonnes {columns}")
                    result['error'] = "Modèle Odoo non reconnu"
                    return result
                
                model_name = mapping_info['model']
                field_mapping = mapping_info['fields']
                model_obj = self.env[model_name]
                
                self.env.cr.execute(f"DELETE FROM {model_obj._table}")
                rows = list(reader)
        
        # Créer le mapping des colonnes du fichier vers les champs Odoo
        file_column_mapping = {}
        for csv_col in columns:
            csv_col_upper = csv_col.upper().strip()
            if csv_col_upper in field_mapping:
                file_column_mapping[csv_col] = field_mapping[csv_col_upper]
        
        # Préparer les données pour insertion
        records_to_create = []
        for row in rows:
            vals = {}
            for csv_col, odoo_field in file_column_mapping.items():
                value = row.get(csv_col, '')
                converted_value = self._convert_value(value, odoo_field, model_obj)
                if converted_value is not False or model_obj._fields[odoo_field].type in ('boolean',):
                    vals[odoo_field] = converted_value
            
            if vals:
                records_to_create.append(vals)
        
        # Créer les enregistrements par lots pour de meilleures performances
        batch_size = 1000
        total_created = 0
        total_records = len(records_to_create)
        _logger.info(f"     Début de l'insertion de {total_records} enregistrements...")
        
        for i in range(0, total_records, batch_size):
            batch = records_to_create[i:i + batch_size]
            model_obj.create(batch)
            total_created += len(batch)
            if total_records > batch_size:
                _logger.info(f"     Progression: {total_created}/{total_records} enregistrements créés ({int(total_created/total_records*100)}%)")
        
        _logger.info(f"     Import terminé: {total_created} enregistrements créés dans {model_name}")
        result['success'] = True
        result['records'] = total_created
        result['table'] = model_obj._table
        return result

    def _move_file_to_folder(self, filepath, folder_name):
        """
        Déplace un fichier dans un sous-dossier avec la date/heure au début du nom
        :param filepath: chemin complet du fichier à déplacer
        :param folder_name: nom du sous-dossier de destination ('archive' ou 'anomalie')
        """
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        
        # Créer le sous-dossier s'il n'existe pas
        dest_dir = os.path.join(directory, folder_name)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            _logger.info(f"     Dossier {folder_name} créé: {dest_dir}")
        
        # Format: YYYYMMDD_HHMMSS_filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{filename}"
        new_filepath = os.path.join(dest_dir, new_filename)
        
        os.rename(filepath, new_filepath)
        _logger.info(f"     Fichier déplacé: {filename} -> {folder_name}/{new_filename}")
        return new_filepath

    @api.model
    def cron_import_csv_files(self):
        """
        Tâche planifiée pour importer les fichiers CSV du dossier configuré
        """
        start_time = time.time()
        
        _logger.info("="*60)
        _logger.info("CEGID IMPORT CSV - DÉBUT DU TRAITEMENT")
        _logger.info("="*60)
        
        # Transférer les fichiers depuis Azure vers le dossier local
        self._transfert_azure_cegid()
        
        companies = self.env['res.company'].search([('is_cegid_csv_path', '!=', False)])
        
        if not companies:
            _logger.warning("Aucune société n'a de dossier CSV Cegid configuré")
            _logger.info("Veuillez configurer le chemin dans l'onglet 'Cegid' de la fiche société")
            elapsed_time = time.time() - start_time
            _logger.info("="*60)
            _logger.info("CEGID IMPORT CSV - FIN DU TRAITEMENT")
            _logger.info(f"  Durée totale: {elapsed_time:.2f} secondes")
            _logger.info("="*60)
            return True
        
        total_files_imported = 0
        total_files_error = 0
        # Listes pour le récapitulatif
        imported_files = []  # [(filename, records, table), ...]
        error_files = []     # [(filename, error_message), ...]
        
        for company in companies:
            csv_path = company.is_cegid_csv_path
            
            _logger.info("-"*40)
            _logger.info(f"Société: {company.name}")
            _logger.info(f"Dossier CSV: {csv_path}")
            
            if not csv_path:
                _logger.warning(f"  -> Aucun dossier indiqué pour cette société")
                continue
            
            if not os.path.isdir(csv_path):
                _logger.error(f"  -> ERREUR: Le dossier n'existe pas ou n'est pas accessible: {csv_path}")
                continue
            
            _logger.info(f"  -> Début de l'import depuis: {csv_path}")
            
            # Lister les fichiers CSV du dossier
            try:
                all_files = os.listdir(csv_path)
                csv_files = [f for f in all_files 
                            if f.lower().endswith('.csv') and not f.endswith('.archive')]
            except PermissionError:
                _logger.error(f"  -> ERREUR: Permission refusée pour accéder au dossier: {csv_path}")
                continue
            except Exception as e:
                _logger.error(f"  -> ERREUR: Impossible de lister le dossier: {str(e)}")
                continue
            
            if not csv_files:
                _logger.info(f"  -> Aucun fichier CSV à importer dans ce dossier")
                archived_files = [f for f in all_files if f.endswith('.archive')]
                if archived_files:
                    _logger.info(f"  -> {len(archived_files)} fichier(s) déjà archivé(s) dans ce dossier")
                continue
            
            _logger.info(f"  -> {len(csv_files)} fichier(s) CSV trouvé(s): {', '.join(csv_files)}")
            
            for csv_file in csv_files:
                filepath = os.path.join(csv_path, csv_file)
                _logger.info(f"  -> Traitement du fichier: {csv_file}")
                
                try:
                    # Importer le fichier
                    result = self._import_csv_file(filepath)
                    
                    if result['success']:
                        # Archiver le fichier
                        self._move_file_to_folder(filepath, 'archive')
                        self.env.cr.commit()
                        _logger.info(f"  -> SUCCÈS: Fichier importé et archivé: {csv_file}")
                        total_files_imported += 1
                        imported_files.append((csv_file, result['records'], result['table']))
                    else:
                        # Déplacer le fichier en anomalie
                        self._move_file_to_folder(filepath, 'anomalie')
                        _logger.warning(f"  -> ÉCHEC: L'import du fichier a échoué, déplacé en anomalie: {csv_file}")
                        total_files_error += 1
                        error_files.append((csv_file, result['error']))
                        
                except Exception as e:
                    error_msg = str(e)
                    _logger.error(f"  -> ERREUR lors de l'import du fichier {csv_file}: {error_msg}")
                    self.env.cr.rollback()
                    # Déplacer le fichier en anomalie
                    try:
                        self._move_file_to_folder(filepath, 'anomalie')
                        _logger.warning(f"  -> Fichier déplacé en anomalie: {csv_file}")
                    except Exception as move_error:
                        _logger.error(f"  -> ERREUR lors du déplacement en anomalie: {str(move_error)}")
                    total_files_error += 1
                    error_files.append((csv_file, error_msg))
                    continue
            
            _logger.info(f"  -> Import terminé pour la société {company.name}")
        
        elapsed_time = time.time() - start_time
        # Formater la durée de manière lisible
        if elapsed_time >= 60:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            duration_str = f"{minutes} min {seconds:.2f} sec"
        else:
            duration_str = f"{elapsed_time:.2f} secondes"
        
        _logger.info("="*80)
        _logger.info("CEGID IMPORT CSV - RÉCAPITULATIF")
        _logger.info("="*80)
        
        # Afficher les fichiers importés avec succès
        if imported_files:
            _logger.info("")
            _logger.info("FICHIERS IMPORTÉS AVEC SUCCÈS:")
            _logger.info("-"*80)
            _logger.info(f"{'Fichier':<50} {'Enregistrements':>15} {'Table Odoo':<20}")
            _logger.info("-"*80)
            for filename, records, table in imported_files:
                # Tronquer le nom du fichier si trop long
                display_name = filename[:47] + '...' if len(filename) > 50 else filename
                _logger.info(f"{display_name:<50} {records:>15} {table:<20}")
            _logger.info("-"*80)
        
        # Afficher les fichiers en anomalie
        if error_files:
            _logger.info("")
            _logger.info("FICHIERS EN ANOMALIE:")
            _logger.info("-"*80)
            _logger.info(f"{'Fichier':<50} {'Erreur':<30}")
            _logger.info("-"*80)
            for filename, error in error_files:
                # Tronquer le nom du fichier et l'erreur si trop longs
                display_name = filename[:47] + '...' if len(filename) > 50 else filename
                display_error = error[:27] + '...' if len(error) > 30 else error
                _logger.info(f"{display_name:<50} {display_error:<30}")
            _logger.info("-"*80)
        
        _logger.info("")
        _logger.info(f"Total fichiers importés: {total_files_imported}")
        _logger.info(f"Total fichiers en erreur: {total_files_error}")
        _logger.info(f"Durée totale: {duration_str}")
        _logger.info("="*80)
        
        return True
