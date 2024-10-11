# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._update_cutoff_accrual_order()
        return res

    def unlink(self):
        # In case the invoice was posted, we need to check any affected cutoff
        self._update_cutoff_accrual_order()
        return super().unlink()

    def _get_cutoff_accrual_order_lines(self):
        """Return a list of order lines to process"""
        self.ensure_one()
        return []

    def _update_cutoff_accrual_order(self):
        for move in self:
            if not move.is_invoice():
                continue
            for model_order_lines in move.sudo()._get_cutoff_accrual_order_lines():
                for order_line in model_order_lines:
                    # In case invoice lines have been created and posted in one
                    # transaction, we need to clear the cache of invoice lines
                    # on the cutoff lines
                    order_line.account_cutoff_line_ids.invalidate_recordset(
                        ["invoice_line_ids"]
                    )
                    order_line._update_cutoff_accrual(move.date)
