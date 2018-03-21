# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    default_prepaid_revenue_account_id = fields.Many2one(
        related='company_id.default_prepaid_revenue_account_id')
    default_prepaid_expense_account_id = fields.Many2one(
        related='company_id.default_prepaid_expense_account_id')
