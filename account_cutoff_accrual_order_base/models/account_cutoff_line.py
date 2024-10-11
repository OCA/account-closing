# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    order_line_model = fields.Selection(related="parent_id.order_line_model")

    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", readonly=True
    )
    received_qty = fields.Float("Received Quantity", readonly=True)
    invoiced_qty = fields.Float("Invoiced Quantity", readonly=True)
    invoice_line_ids = fields.One2many(
        "account.move.line",
        compute="_compute_invoice_lines",
        string="Invoice Lines",
    )
    quantity = fields.Float(compute="_compute_quantity", store=True)
    amount = fields.Monetary(compute="_compute_amount", store=True)
    cutoff_amount = fields.Monetary(compute="_compute_cutoff_amount", store=True)

    def _get_order_line(self):
        self.ensure_one()
        return

    def _compute_invoice_lines(self):
        return

    @api.depends("invoiced_qty", "received_qty")
    def _compute_quantity(self):
        for rec in self:
            if not rec.parent_id.order_line_model:
                continue
            rec.quantity = rec.received_qty - rec.invoiced_qty

    @api.depends("price_unit", "quantity")
    def _compute_amount(self):
        for rec in self:
            if not rec.parent_id.order_line_model:
                continue
            if rec.parent_id.cutoff_type == "accrued_revenue":
                amount = rec.quantity * rec.price_unit
            elif rec.parent_id.cutoff_type == "accrued_expense":
                amount = -rec.quantity * rec.price_unit
            else:
                continue
            rec.amount = rec.company_currency_id.round(amount)

    @api.depends("amount")
    def _compute_cutoff_amount(self):
        for rec in self:
            if not rec.parent_id.order_line_model:
                continue
            if rec.parent_id.state == "done":
                continue
            if rec.company_currency_id != rec.currency_id:
                currency_at_date = rec.currency_id.with_context(
                    date=rec.parent_id.cutoff_date
                )
                rec.cutoff_amount = currency_at_date.compute(
                    rec.amount, rec.company_currency_id
                )
            else:
                rec.cutoff_amount = rec.amount
