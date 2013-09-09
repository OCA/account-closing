# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line", string="Sale Order Line", readonly=True
    )
    purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line", string="Purchase Order Line", readonly=True
    )
    order_id = fields.Char(
        "Order",
        compute="_compute_order_line",
    )
    product_id = fields.Many2one(
        "product.product",
        compute="_compute_order_line",
        store=True,
        string="Product",
    )
    received_qty = fields.Float("Received Quantity", readonly=True)
    invoice_line_ids = fields.One2many(
        "account.move.line",
        compute="_compute_order_line",
        string="Invoice Lines",
    )
    # Do not declare as compute field as flush_recordset will recompute it and bloat cache
    invoiced_qty = fields.Float("Invoiced Quantity", readonly=True)
    quantity = fields.Float(compute="_compute_quantity", store=True)
    amount = fields.Monetary(compute="_compute_amount", store=True)
    cutoff_amount = fields.Monetary(compute="_compute_cutoff_amount", store=True)
    tax_line_ids = fields.One2many(compute="_compute_tax_lines", store=True)

    @api.depends("sale_line_id", "purchase_line_id")
    def _compute_order_line(self):
        for rec in self:
            if rec.sale_line_id:
                line = rec.sale_line_id
                rec.order_id = line.order_id.name
                rec.product_id = line.product_id
                rec.invoice_line_ids = line.invoice_lines
            elif rec.purchase_line_id:
                line = rec.purchase_line_id
                rec.order_id = line.order_id.name
                rec.product_id = line.product_id
                rec.invoice_line_ids = line.invoice_lines
            else:
                rec.order_id = False
                rec.product_id = False
                rec.invoice_line_ids = False

    def _compute_received_qty(self):
        cutoff_nextday = self.parent_id._nextday_start_dt()
        for rec in self:
            if rec.parent_id.state == "done":
                continue
            if rec.purchase_line_id:
                line = rec.purchase_line_id
                received_qty = line.qty_received
                # Processing purchase order line
                # The quantity received on the PO line must be deducted from all
                # moves done after the cutoff date.
                moves_after = line.move_ids.filtered(
                    lambda m: m.state == "done" and m.date >= cutoff_nextday
                )
                for move in moves_after:
                    if move.product_uom != line.product_uom:
                        received_qty -= move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom
                        )
                    else:
                        received_qty -= move.product_uom_qty
                rec.received_qty = received_qty
            elif rec.sale_line_id:
                line = rec.sale_line_id
                received_qty = line.qty_delivered
                # Processing sale order line
                # The quantity received on the SO line must be deducted from all
                # moves done after the cutoff date.
                moves_after = (
                    line.order_id.procurement_group_id.stock_move_ids.filtered(
                        lambda r: r.state == "done" and r.date >= cutoff_nextday
                    )
                )
                for move in moves_after:
                    if move.product_uom != line.product_uom:
                        received_qty -= move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom
                        )
                    else:
                        received_qty -= move.product_uom_qty
                rec.received_qty = received_qty
            else:
                rec.received_qty = 0

    def _compute_invoiced_qty(self):
        for rec in self:
            if not rec.sale_line_id and not rec.purchase_line_id:
                continue
            cutoff_nextday = rec.parent_id._nextday_start_dt()
            invoiced_qty = sum(
                line.quantity
                * (-1 if line.move_id.move_type in ("in_refund", "out_refund") else 1)
                for line in rec.invoice_line_ids
                if (
                    line.move_id.state == "posted"
                    and line.move_id.date <= rec.parent_id.cutoff_date
                )
                or (
                    line.move_id.state == "draft"
                    and line.move_id.move_type == "in_refund"
                    and line.move_id.create_date < cutoff_nextday
                )
            )
            if rec.parent_id.state == "done" and invoiced_qty != rec.invoiced_qty:
                raise UserError(
                    _(
                        "You cannot validate an invoice for an accounting date "
                        "that modifies a closed cutoff (i.e. for which an "
                        "accounting entry has already been created).\n"
                        " - Cut-off: {cutoff}\n"
                        " - Product: {product}\n"
                        " - Previous invoiced quantity: {prev_inv_qty}\n"
                        " - New invoiced quantity: {new_inv_qty}"
                    ).format(
                        cutoff=rec.parent_id.display_name,
                        product=rec.product_id.display_name,
                        prev_inv_qty=rec.invoiced_qty,
                        new_inv_qty=invoiced_qty,
                    )
                )
            rec.invoiced_qty = invoiced_qty

    @api.depends("invoiced_qty", "received_qty")
    def _compute_quantity(self):
        for rec in self:
            if not rec.sale_line_id and not rec.purchase_line_id:
                continue
            rec.quantity = rec.received_qty - rec.invoiced_qty

    @api.depends("price_unit", "quantity")
    def _compute_amount(self):
        for rec in self:
            if rec.sale_line_id:
                amount = rec.quantity * rec.price_unit
            elif rec.purchase_line_id:
                amount = -rec.quantity * rec.price_unit
            else:
                continue
            rec.amount = rec.company_currency_id.round(amount)

    @api.depends("amount")
    def _compute_cutoff_amount(self):
        for rec in self:
            if rec.parent_id.state == "done":
                continue
            if not rec.sale_line_id and not rec.purchase_line_id:
                continue
            if self.company_currency_id != self.currency_id:
                currency_at_date = self.currency_id.with_context(date=self.cutoff_date)
                rec.cutoff_amount = currency_at_date.compute(
                    rec.amount, self.company_currency_id
                )
            else:
                rec.cutoff_amount = rec.amount

    @api.depends("sale_line_id", "purchase_line_id", "quantity")
    def _compute_tax_lines(self):
        if not self.env.company.accrual_taxes:
            return
        for rec in self:
            if rec.parent_id.state == "done":
                continue
            if rec.sale_line_id:
                line = rec.sale_line_id
                tax_account_field_name = "account_accrued_revenue_id"
                tax_account_field_label = "Accrued Revenue Tax Account"
                sign = 1
            elif rec.purchase_line_id:
                line = rec.purchase_line_id
                tax_account_field_name = "account_accrued_expense_id"
                tax_account_field_label = "Accrued Expense Tax Account"
                sign = -1
            else:
                continue
            tax_line_ids = [Command.clear()]
            base_line = line._convert_to_tax_base_line_dict()
            base_line["quantity"] = rec.quantity
            tax_info = self.env["account.tax"]._compute_taxes([base_line])
            for tax_line in tax_info["tax_lines_to_add"]:
                amount = tax_line["tax_amount"] * sign
                if self.company_currency_id != self.currency_id:
                    currency_at_date = self.currency_id.with_context(
                        date=self.parent_id.cutoff_date
                    )
                    tax_cutoff_amount = currency_at_date.compute(
                        amount, self.company_currency_id
                    )
                else:
                    tax_cutoff_amount = amount
                tax = self.env["account.tax"].browse(tax_line["tax_id"])
                tax_cutoff_account_id = tax[tax_account_field_name]
                if not tax_cutoff_account_id:
                    raise UserError(
                        _(
                            "Error: Missing '%(label)s' on tax '%(name)s'.",
                            label=tax_account_field_label,
                            name=tax.display_name,
                        )
                    )
                tax_line_ids.append(
                    Command.create(
                        {
                            "tax_id": tax_line["tax_id"],
                            "base": tax_line["base_amount"],
                            "amount": amount,
                            "cutoff_account_id": tax_cutoff_account_id.id,
                            "cutoff_amount": tax_cutoff_amount,
                        },
                    )
                )
            rec.tax_line_ids = tax_line_ids
