# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    default_accrued_revenue_account_id = fields.Many2one(
        related='company_id.default_accrued_revenue_account_id')
    default_accrued_expense_account_id = fields.Many2one(
        related='company_id.default_accrued_expense_account_id')
    default_accrual_revenue_journal_id = fields.Many2one(
        related='company_id.default_accrual_revenue_journal_id')
    default_accrual_expense_journal_id = fields.Many2one(
        related='company_id.default_accrual_expense_journal_id')
