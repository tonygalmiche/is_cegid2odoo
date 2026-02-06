# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IsCegidAbsencesalarie(models.Model):
    _name = 'is.cegid.absencesalarie'
    _description = 'Cegid - Absences Salariés'
    _order = 'pcn_salarie, pcn_datedebutabs desc'

    pcn_typemvt = fields.Char(string='Type Mvt', index=True)
    pcn_salarie = fields.Char(string='Salarié', index=True)
    pcn_ordre = fields.Integer(string='Ordre')
    pcn_periodecp = fields.Integer(string='Période CP')
    pcn_typeconge = fields.Char(string='Type Congé', index=True)
    pcn_sensabs = fields.Char(string='Sens Abs')
    pcn_libelle = fields.Char(string='Libellé')
    pcn_datedebutabs = fields.Datetime(string='Date Début Abs', index=True)
    pcn_debutdj = fields.Char(string='Début DJ')
    pcn_datefinabs = fields.Datetime(string='Date Fin Abs')
    pcn_findj = fields.Char(string='Fin DJ')
    pcn_jours = fields.Float(string='Jours', digits=(10, 2))
    pcn_heures = fields.Float(string='Heures', digits=(10, 2))
    pcn_guid = fields.Char(string='GUID')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.pcn_salarie} - {record.pcn_libelle or record.pcn_typeconge or ''}"
            result.append((record.id, name))
        return result
