# Copyright 2016-2022 Akretion France
# Copyright 2026 Tecnativa - Adasat Torres
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    pending_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    previous_pending_amount = fields.Monetary(
        currency_field="currency_id", readonly=True
    )
    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)
    total_days = fields.Integer(readonly=True)
    cutoff_days = fields.Integer(
        readonly=True,
        help="In regular mode, this is the number of days after the "
        "cut-off date. In forecast mode, this is the number of days "
        "between the start date and the end date.",
    )


class AccountCutoffTaxLine(models.Model):
    _inherit = "account.cutoff.tax.line"

    pending_base = fields.Monetary(currency_field="currency_id", readonly=True)
    pending_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    pending_cutoff_amount = fields.Monetary(
        currency_field="company_currency_id", readonly=True
    )
