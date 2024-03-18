# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "order.line.cutoff.accrual.mixin"]

    def _get_cutoff_accrual_lines_delivered_after(self, cutoff):
        lines = super()._get_cutoff_accrual_lines_delivered_after(cutoff)
        cutoff_nextday = cutoff._nextday_start_dt()
        # Take all moves done after the cutoff date
        moves_after = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("date", ">=", cutoff_nextday),
                ("sale_line_id", "!=", False),
            ],
            order="id",
        )
        sale_ids = set(moves_after.sale_line_id.order_id.ids)
        sales = self.env["sale.order"].browse(sale_ids)
        lines |= sales.order_line
        return lines

    def _get_cutoff_accrual_delivered_min_date(self):
        """Return first delivery date"""
        self.ensure_one()
        stock_moves = self.move_ids.filtered(lambda m: m.state == "done")
        if not stock_moves:
            return
        return min(stock_moves.mapped("date")).date()

    def _get_cutoff_accrual_delivered_stock_quantity(self, cutoff):
        self.ensure_one()
        delivered_qty = self.qty_delivered
        # The quantity delivered on the SO line must be deducted from all
        # moves done after the cutoff date.
        cutoff_nextday = cutoff._nextday_start_dt()
        out_moves, in_moves = self._get_outgoing_incoming_moves()
        for move in out_moves:
            if move.state != "done" or move.date < cutoff_nextday:
                continue
            delivered_qty -= move.product_uom._compute_quantity(
                move.product_uom_qty,
                self.product_uom,
                rounding_method="HALF-UP",
            )
        for move in in_moves:
            if move.state != "done" or move.date < cutoff_nextday:
                continue
            delivered_qty += move.product_uom._compute_quantity(
                move.product_uom_qty,
                self.product_uom,
                rounding_method="HALF-UP",
            )
        return delivered_qty
