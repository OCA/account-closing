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
        # In SQL to reduce memory usage as we could process large dataset
        self.env.cr.execute(
            """
            SELECT order_id
            FROM sale_order_line
            WHERE id in (
                SELECT sale_line_id
                FROM stock_move
                WHERE state='done'
                  AND date >= %s
                  AND sale_line_id IS NOT NULL
            )
        """,
            (cutoff_nextday,),
        )
        sale_ids = [x[0] for x in self.env.cr.fetchall()]
        lines = self.env["sale.order.line"].search(
            ["|", ("order_id", "in", sale_ids), ("id", "in", lines.ids)], order="id"
        )
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
        cutoff_nextday = cutoff._nextday_start_dt()
        if self.create_date >= cutoff_nextday:
            # A line added after the cutoff cannot be delivered in the past
            return 0
        delivered_qty = self.qty_delivered
        # The quantity delivered on the SO line must be deducted from all
        # moves done after the cutoff date.
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
