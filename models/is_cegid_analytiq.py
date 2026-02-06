# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsCegidAnalytiq(models.Model):
    _name = 'is.cegid.analytiq'
    _description = 'Cegid - Écritures Analytiques'
    _order = 'y_datecomptable desc, y_refinterne'

    y_datecomptable = fields.Datetime(string='Date Comptable', index=True)
    y_general = fields.Char(string='Général', index=True)
    y_axe = fields.Char(string='Axe', index=True)
    y_section = fields.Char(string='Section', index=True)
    y_refinterne = fields.Integer(string='Réf. Interne')
    y_libelle = fields.Char(string='Libellé')
    y_naturepiece = fields.Char(string='Nature Pièce')
    y_refexterne = fields.Char(string='Réf. Externe')
    y_journal = fields.Char(string='Journal', index=True)
    y_contrepartieaux = fields.Char(string='Contrepartie Aux.')
    y_debit = fields.Float(string='Débit', digits=(12, 2))
    y_credit = fields.Float(string='Crédit', digits=(12, 2))

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.y_refinterne} - {record.y_libelle or ''}"
            result.append((record.id, name))
        return result
