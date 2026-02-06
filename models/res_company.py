# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_cegid_csv_path = fields.Char(
        string='Chemin dossier CSV Cegid',
        help="Chemin absolu vers le dossier contenant les fichiers CSV Cegid à importer"
    )
