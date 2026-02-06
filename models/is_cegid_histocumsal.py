# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsCegidHistocumsal(models.Model):
    _name = 'is.cegid.histocumsal'
    _description = 'Cegid - Historique Cumuls Salaires'
    _order = 'phc_salarie, phc_cumulpaie'

    phc_salarie = fields.Char(string='Salarié', required=True, index=True)
    phc_cumulpaie = fields.Char(string='Cumul Paie', required=True, index=True)
    phc_montant = fields.Float(string='Montant', digits=(12, 2))

    _sql_constraints = [
        ('salarie_cumulpaie_unique', 
         'UNIQUE(phc_salarie, phc_cumulpaie)', 
         'La combinaison Salarié/Cumul Paie doit être unique!')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.phc_salarie} - {record.phc_cumulpaie}"
            result.append((record.id, name))
        return result
