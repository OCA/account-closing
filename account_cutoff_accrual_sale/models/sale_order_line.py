# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "order.line.cutoff.accrual.mixin"]

    account_cutoff_line_ids = fields.One2many(
        "account.cutoff.line",
        "sale_line_id",
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
            # If the order is not to invoice
            rec.is_cutoff_accrual_excluded = rec.order_id.force_invoiced

    def _get_cutoff_accrual_partner(self):
        return self.order_id.partner_invoice_id

    def _get_cutoff_accrual_product_qty(self):
        return self.product_uom_qty

    def _get_cutoff_accrual_lines_domain(self, cutoff):
        domain = super()._get_cutoff_accrual_lines_domain(cutoff)
        # The line could be invoiceable but not the order (see delivery
        # module).
        domain.append(("invoice_status", "=", "to invoice"))
        domain.append(("order_id.invoice_status", "=", "to invoice"))
        return domain

    def _prepare_cutoff_accrual_line(self, cutoff):
        res = super()._prepare_cutoff_accrual_line(cutoff)
        if not res:
            return
        res["sale_line_id"] = self.id
        return res

    def _get_cutoff_accrual_lines_invoiced_after(self, cutoff):
        cutoff_nextday = cutoff._nextday_start_dt()
        # Take all invoices impacting the cutoff
        # FIXME: what about ("move_id.payment_state", "=", "invoicing_legacy")
        domain = [
            ("sale_line_ids.is_cutoff_accrual_excluded", "!=", True),
            ("move_id.move_type", "in", ("out_invoice", "out_refund")),
            ("sale_line_ids", "!=", False),
            "|",
            ("move_id.state", "=", "draft"),
            "&",
            ("move_id.state", "=", "posted"),
            ("move_id.date", ">=", cutoff_nextday),
        ]
        invoice_line_after = self.env["account.move.line"].search(domain, order="id")
        _logger.debug(
            "Sales Invoice Lines done after cutoff: %s" % len(invoice_line_after)
        )
        if not invoice_line_after:
            return self.env["sale.order.line"]
        # In SQL to reduce memory usage as we could process large dataset
        self.env.cr.execute(
            """
            SELECT order_id
            FROM sale_order_line
            WHERE id in (
                SELECT order_line_id
                FROM sale_order_line_invoice_rel
                WHERE invoice_line_id in %s
            )
            """,
            (tuple(invoice_line_after.ids),),
        )
        sale_ids = [x[0] for x in self.env.cr.fetchall()]
        lines = self.env["sale.order.line"].search(
            [("order_id", "in", sale_ids)], order="id"
        )
        return lines

    def _get_cutoff_accrual_delivered_service_quantity(self, cutoff):
        self.ensure_one()
        cutoff_nextday = cutoff._nextday_start_dt()
        if self.create_date >= cutoff_nextday:
            # A line added after the cutoff cannot be delivered in the past
            return 0
        if self.product_id.invoice_policy == "order":
            return self.product_uom_qty
        return self.qty_delivered

    def _get_cutoff_accrual_delivered_stock_quantity(self, cutoff):
        self.ensure_one()
        cutoff_nextday = cutoff._nextday_start_dt()
        if self.create_date >= cutoff_nextday:
            # A line added after the cutoff cannot be delivered in the past
            return 0
        if self.product_id.invoice_policy == "order":
            return self.product_uom_qty
        return self.qty_delivered
