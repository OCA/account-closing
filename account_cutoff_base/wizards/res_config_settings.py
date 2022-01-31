# Copyright 2013-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # I can't name it default_cutoff_journal_id
    # because default_ is a special prefix
    dft_cutoff_journal_id = fields.Many2one(
        related="company_id.default_cutoff_journal_id",
        readonly=False,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    dft_cutoff_move_partner = fields.Boolean(
        related="company_id.default_cutoff_move_partner", readonly=False
    )
    accrual_taxes = fields.Boolean(related="company_id.accrual_taxes", readonly=False)
    dft_accrued_revenue_account_id = fields.Many2one(
        related="company_id.default_accrued_revenue_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
    dft_accrued_expense_account_id = fields.Many2one(
        related="company_id.default_accrued_expense_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
    dft_prepaid_revenue_account_id = fields.Many2one(
        related="company_id.default_prepaid_revenue_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
    dft_prepaid_expense_account_id = fields.Many2one(
        related="company_id.default_prepaid_expense_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
