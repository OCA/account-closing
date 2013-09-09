# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._cutoff_picking_update()
        return res

    def unlink(self):
        # In case the invoice was posted, we need to check any affected cutoff
        self._cutoff_picking_update()
        return super().unlink()

    def _cutoff_picking_update(self):
        for move in self:
            values = []
            if not move.is_invoice():
                continue
            if move.move_type in ("out_invoice", "out_refund"):
                order_lines = move.invoice_line_ids.sale_line_ids
            elif move.move_type in ("in_invoice", "in_refund"):
                order_lines = move.invoice_line_ids.purchase_line_id
            else:
                continue
            for order_line in order_lines:
                if (
                    order_line.order_id.state == "done"
                    and self.env.company.cutoff_exclude_locked_orders
                ):
                    continue
                order_line.account_cutoff_line_ids.invalidate_recordset(
                    ["invoice_line_ids"]
                )
                order_line.account_cutoff_line_ids._compute_invoiced_qty()
                # search missing cutoff entries - start at first reception
                stock_moves = order_line.move_ids.filtered(lambda m: m.state == "done")
                if stock_moves:
                    stock_move_date = (min(stock_moves.mapped("date"))).date()
                    date = min(stock_move_date, move.date)
                else:
                    date = move.date
                cutoffs = self.env["account.cutoff"].search(
                    [
                        ("cutoff_date", ">=", date),
                        (
                            "id",
                            "not in",
                            order_line.account_cutoff_line_ids.parent_id.ids,
                        ),
                        ("cutoff_type", "in", ("accrued_expense", "accrued_revenue")),
                    ]
                )
                for cutoff in cutoffs:
                    data = cutoff._prepare_line(order_line)
                    if not data:
                        continue
                    if cutoff.state == "done":
                        raise UserError(
                            _(
                                "You cannot validate an invoice for an accounting date "
                                "that generates an entry in a closed cut-off (i.e. for "
                                "which an accounting entry has already been created).\n"
                                " - Cut-off: %(cutoff)s\n"
                                " - Product: %(product)s\n"
                            ).format(
                                cutoff=cutoff.display_name,
                                product=order_line.product_id.display_name,
                            )
                        )
                    values.append(data)
            self.env["account.cutoff"]._create_cutoff_lines(values)
