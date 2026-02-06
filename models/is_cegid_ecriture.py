# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsCegidEcriture(models.Model):
    _name = 'is.cegid.ecriture'
    _description = 'Cegid - Écritures Comptables'
    _order = 'e_datecomptable desc, e_refinterne'

    e_datecomptable = fields.Datetime(string='Date Comptable', index=True)
    e_refinterne = fields.Char(string='Réf. Interne', index=True)
    e_libelle = fields.Char(string='Libellé')
    e_general = fields.Char(string='Général', index=True)
    e_debit = fields.Float(string='Débit', digits=(12, 2))
    e_credit = fields.Float(string='Crédit', digits=(12, 2))
    e_auxiliaire = fields.Char(string='Auxiliaire', index=True)
    e_reflibre = fields.Char(string='Réf. Libre')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.e_refinterne} - {record.e_libelle or ''}"
            result.append((record.id, name))
        return result
