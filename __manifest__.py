# -*- coding: utf-8 -*-
{
    'name': 'Import Cegid vers Odoo',
    'version': '16.0.1.1.0',
    'summary': 'Module Odoo 16 pour Plastigray pour importer des tables Cegid dans Odoo',
    'description': """
        Module permettant d'importer des tables de Cegid dans Odoo.
        Tables importées :
        - HISTOCUMSAL : Historique des cumuls de salaires
        - ECRITURE : Écritures comptables
        - ABSENCESALARIE : Absences des salariés
        - ANALYTIQ : Écritures analytiques
        
        Fonctionnalités :
        - Import automatique des fichiers CSV via tâche planifiée
        - Configuration du chemin des fichiers CSV dans la fiche société
        - Archivage automatique des fichiers importés
    """,
    "author"   : "InfoSaône",
    "category" : "InfoSaône",
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/is_cegid_security.xml',
        'security/ir.model.access.csv',
        'views/is_cegid_histocumsal_views.xml',
        'views/is_cegid_ecriture_views.xml',
        'views/is_cegid_absencesalarie_views.xml',
        'views/is_cegid_analytiq_views.xml',
        'views/res_company_views.xml',
        'views/is_cegid_menus.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
