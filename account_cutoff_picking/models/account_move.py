# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        if self.is_invoice():
            self.invoice_line_ids._update_cutoff()
        return res

    def unlink(self):
        acli = self.env["account.cutoff.line.invoice"].search(
            [("move_line_id", "in", self.mapped("invoice_line_ids").ids)]
        )
        if acli:
            if "done" in acli.mapped("cutoff_line_id.parent_id.state"):
                raise UserError(
                    _(
                        "You cannot delete an invoice for an accounting date "
                        "where the cutoff accounting entry has already been "
                        "created"
                    )
                )
            acli.unlink()
        return super().unlink()
