# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)

    @api.model
    def _select(self) -> SQL:
        return SQL("%s, line.start_date, line.end_date", super()._select())
