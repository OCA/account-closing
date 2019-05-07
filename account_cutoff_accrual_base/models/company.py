# Copyright 2013-2018 Akretion (http://www.akretion.com)
# Copyright 2017 ACSONE SA/NV
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_accrued_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Account for Accrued Revenues',
        domain=[('deprecated', '=', False)])

    default_accrued_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Account for Accrued Expenses',
        domain=[('deprecated', '=', False)])

    accrual_taxes = fields.Boolean(string='Accrual On Taxes')
