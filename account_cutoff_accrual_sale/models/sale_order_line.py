# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models
from odoo.osv import expression

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

    def _get_cutoff_accrual_price_unit(self):
        if self.is_downpayment:
            return self.price_unit
        return super()._get_cutoff_accrual_price_unit()

    @api.model
    def _get_cutoff_accrual_lines_domain(self, cutoff):
        domain = super()._get_cutoff_accrual_lines_domain(cutoff)
        domain = expression.AND(
            (
                domain,
                (
                    ("state", "in", ("sale", "done")),
                    ("display_type", "=", False),
                ),
            )
        )
        return domain

    @api.model
    def _get_cutoff_accrual_lines_query(self, cutoff):
        query = super()._get_cutoff_accrual_lines_query(cutoff)
        self.flush_model(
            [
                "qty_delivered_method",
                "qty_delivered",
                "qty_invoiced",
                "qty_to_invoice",
                "is_downpayment",
            ]
        )
        # The delivery line could be invoiceable but not the order (see
        # delivery module). So check also the SO invoice status.
        so_alias = query.join(
            self._table, "order_id", self.order_id._table, "id", "order_id"
        )
        self.order_id.flush_model(["invoice_status"])
        # For stock products, we always consider the delivered quantity as it
        # impacts the stock valuation.
        # Otherwise, we consider the invoice policy by checking the
        # qty_to_invoice.
        query.add_where(
            f"""
            CASE
              WHEN "{self._table}".qty_delivered_method = 'stock_move'
                THEN "{self._table}".qty_delivered != "{self._table}".qty_invoiced
              ELSE "{self._table}".qty_to_invoice != 0
                AND (
                  "{so_alias}".invoice_status = 'to invoice'
                  OR "{self._table}".is_downpayment
                )
              END
            """
        )
        return query

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
        # In case of service, we consider what should be invoiced and this is
        # given by the invoice policy.
        if self.product_id.invoice_policy == "order":
            return self.product_uom_qty
        return self.qty_delivered

    def _get_cutoff_accrual_delivered_stock_quantity(self, cutoff):
        self.ensure_one()
        cutoff_nextday = cutoff._nextday_start_dt()
        if self.create_date >= cutoff_nextday:
            # A line added after the cutoff cannot be delivered in the past
            return 0
        # In case of stock, we always consider what is delivered as this
        # impacted the stock valuation.
        return self.qty_delivered

    def _get_cutoff_accrual_delivered_min_date(self):
        """Return first delivery date"""
        self.ensure_one()
        if self.product_id.invoice_policy == "order":
            date_local = self.order_id.date_order
            company_tz = self.env.company.partner_id.tz or "UTC"
            date_utc = fields.Datetime.context_timestamp(
                self.with_context(tz=company_tz),
                date_local,
            )
            return date_utc.date()
        return
