# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "order.line.cutoff.accrual.mixin"]

    account_cutoff_line_ids = fields.One2many(
        "account.cutoff.line",
        "purchase_line_id",
        string="Account Cutoff Lines",
        readonly=True,
    )

    is_cutoff_accrual_excluded = fields.Boolean(
        compute="_compute_is_cutoff_accrual_excluded",
        store=True,
    )

    @api.depends("order_id.force_invoiced")
    def _compute_is_cutoff_accrual_excluded(self):
        for rec in self:
            rec.is_cutoff_accrual_excluded = rec.order_id.force_invoiced

    def _get_cutoff_accrual_lines_domain(self, cutoff):
        domain = super()._get_cutoff_accrual_lines_domain(cutoff)
        domain.append(("order_id.state", "in", ("purchase", "done")))
        domain.append(("order_id.invoice_status", "!=", "invoiced"))
        return domain

    @api.model
    def _get_cutoff_accrual_lines_query(self, cutoff):
        query = super()._get_cutoff_accrual_lines_query(cutoff)
        self.flush_model(["display_type", "qty_received", "qty_invoiced"])
        query.add_where(
            f'"{self._table}".display_type IS NULL AND '
            f'"{self._table}".qty_received != "{self._table}".qty_invoiced'
        )
        return query

    def _prepare_cutoff_accrual_line(self, cutoff):
        res = super()._prepare_cutoff_accrual_line(cutoff)
        if not res:
            return
        res["purchase_line_id"] = self.id
        return res

    def _get_cutoff_accrual_lines_invoiced_after(self, cutoff):
        cutoff_nextday = cutoff._nextday_start_dt()
        # Take all invoices impacting the cutoff
        # FIXME: what about ("move_id.payment_state", "=", "invoicing_legacy")
        domain = [
            ("purchase_line_id.is_cutoff_accrual_excluded", "!=", True),
            ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ("purchase_line_id", "!=", False),
            "|",
            ("move_id.state", "=", "draft"),
            "&",
            ("move_id.state", "=", "posted"),
            ("move_id.date", ">=", cutoff_nextday),
        ]
        invoice_line_after = self.env["account.move.line"].search(domain, order="id")
        _logger.debug(
            "Purchase Invoice Lines done after cutoff: %s" % len(invoice_line_after)
        )
        if not invoice_line_after:
            return self.env["purchase.order.line"]
        # In SQL to reduce memory usage as we could process large dataset
        self.env.cr.execute(
            """
            SELECT order_id
            FROM purchase_order_line
            WHERE id in (
                SELECT purchase_line_id
                FROM account_move_line
                WHERE id in %s
            )
            """,
            (tuple(invoice_line_after.ids),),
        )
        purchase_ids = [x[0] for x in self.env.cr.fetchall()]
        lines = self.env["purchase.order.line"].search(
            [("order_id", "in", purchase_ids)], order="id"
        )
        return lines

    def _get_cutoff_accrual_delivered_service_quantity(self, cutoff):
        # By default, no cutoff on purchase. Set received as invoiced.
        self.ensure_one()
        return self._get_cutoff_accrual_invoiced_quantity(cutoff)

    def _get_cutoff_accrual_delivered_stock_quantity(self, cutoff):
        # By default, no cutoff on purchase. Set received as invoiced.
        self.ensure_one()
        return self._get_cutoff_accrual_invoiced_quantity(cutoff)
