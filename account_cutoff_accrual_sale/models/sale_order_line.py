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
            rec.is_cutoff_accrual_excluded = rec.order_id.force_invoiced

    def _get_cutoff_accrual_partner(self):
        return self.order_id.partner_invoice_id

    def _get_cutoff_accrual_product_qty(self):
        return self.product_uom_qty

    def _get_cutoff_accrual_lines_domain(self):
        domain = super()._get_cutoff_accrual_lines_domain()
        domain.append(("order_id.state", "in", ("sale", "done")))
        domain.append(("order_id.invoice_status", "!=", "invoiced"))
        return domain

    @api.model
    def _get_cutoff_accrual_lines_query(self):
        query = super()._get_cutoff_accrual_lines_query()
        self.flush_model(
            ["display_type", "product_uom_qty", "qty_delivered", "qty_invoiced"]
        )
        product_alias = query.left_join(
            self._table,
            "product_id",
            self.env["product.product"]._table,
            "id",
            "product_id",
        )
        product_tmpl_alias = query.left_join(
            product_alias,
            "product_tmpl_id",
            self.env["product.template"]._table,
            "id",
            "product_tmpl_id",
        )
        query.add_where(
            f"""
            "{self._table}".display_type IS NULL AND
            CASE WHEN
                "{self._table}".product_id IS NOT NULL
                AND "{product_tmpl_alias}".invoice_policy = 'order'
            THEN "{self._table}".product_uom_qty != "{self._table}".qty_invoiced
            ELSE "{self._table}".qty_delivered != "{self._table}".qty_invoiced
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
        sale_ids = set(invoice_line_after.sale_line_ids.order_id.ids)
        sales = self.env["sale.order"].browse(sale_ids)
        return sales.order_line

    def _get_cutoff_accrual_delivered_service_quantity(self, cutoff):
        self.ensure_one()
        if self.product_id.invoice_policy == "order":
            return self.product_uom_qty
        return self.qty_delivered

    def _get_cutoff_accrual_delivered_stock_quantity(self, cutoff):
        self.ensure_one()
        if self.product_id.invoice_policy == "order":
            return self.product_uom_qty
        return self.qty_delivered
