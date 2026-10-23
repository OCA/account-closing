# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)

    def _select_list(self, table):
        return [*super()._select_list(table), table.start_date, table.end_date]
