# Copyright 2026 Lorenzo Battistini
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("invoice_date")
    def _onchange_invoice_date_start_end_dates(self):
        # In the invoice form, the lines that are not saved yet are only in
        # invoice_line_ids: the ORM reaches the lines of a move through
        # line_ids, so changing the invoice date doesn't recompute their dates.
        self.invoice_line_ids._compute_start_end_dates()
