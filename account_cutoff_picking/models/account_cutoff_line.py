# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
        compute="_compute_order_id",
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", readonly=True
    )
    received_qty = fields.Float("Received Quantity", readonly=True)
    invoiced_qty_ids = fields.One2many(
        "account.cutoff.line.invoice",
        "cutoff_line_id",
        "Invoice Lines",
        readonly=True,
    )
    invoiced_qty = fields.Float(
        "Invoiced Quantity", compute="_compute_invoiced_qty", store=True
    )

    @api.depends("invoiced_qty_ids.quantity")
    def _compute_invoiced_qty(self):
        # Only validated invoices and draft expense refunds are in
        # invoiced_qty_ids.  If an invoice is cancelled afterwards, we keep it
        # in the cutoff as we consider it will be revalidated.
        for rec in self:
            rec.invoiced_qty = sum(rec.invoiced_qty_ids.mapped("quantity"))

    @api.constrains("invoiced_qty")
    def _update_invoiced_qty(self):
        for rec in self:
            rec.quantity = rec.received_qty - rec.invoiced_qty

    @api.depends("sale_line_id", "purchase_line_id")
    def _compute_order_id(self):
        for rec in self:
            if rec.sale_line_id:
                rec.order_id = rec.sale_line_id.order_id.name
            elif rec.purchase_line_id:
                rec.order_id = rec.purchase_line_id.order_id.name

    def _get_tax_info(self):
        self.ensure_one()
        if self.sale_line_id:
            taxes = self.sale_line_id.tax_id
        else:
            taxes = self.purchase_line_id.taxes_id
        return taxes.compute_all(
            self.price_unit,
            self.currency_id,
            self.quantity,
            self.product_id,
            self.partner_id,
        )

    def _get_amount(self):
        self.ensure_one()
        tax_info = self._get_tax_info()
        amount = tax_info["total_excluded"]
        if self.parent_id.cutoff_type == "accrued_expense":
            amount = amount * -1
        return amount

    def _get_tax_values(self):
        tax_line_ids = [Command.clear()]
        company = self.env.user.company_id
        self.ensure_one()
        tax_info = self._get_tax_info()
        if self.parent_id.cutoff_type == "accrued_expense":
            tax_account_field_name = "account_accrued_expense_id"
            tax_account_field_label = "Accrued Expense Tax Account"
        elif self.parent_id.cutoff_type == "accrued_revenue":
            tax_account_field_name = "account_accrued_revenue_id"
            tax_account_field_label = "Accrued Revenue Tax Account"
        for tax_line in tax_info["taxes"]:
            tax_read = self.env["account.tax"].browse(tax_line["id"])
            tax_cutoff_account_id = tax_read[tax_account_field_name]
            if not tax_cutoff_account_id:
                if not company.cutoff_taxes:
                    continue
                raise UserError(
                    _(
                        "Error: Missing '%(label)s' on tax '%(name)s'.",
                        label=tax_account_field_label,
                        name=tax_read["name"],
                    )
                )
            tax_cutoff_account_id = tax_cutoff_account_id[0]
            if self.parent_id.cutoff_type == "accrued_expense":
                tax_line["amount"] = tax_line["amount"] * -1
            if self.company_currency_id != self.currency_id:
                currency_at_date = self.currency_id.with_context(
                    date=self.parent_id.cutoff_date
                )
                tax_cutoff_amount = currency_at_date.compute(
                    tax_line["amount"], self.company_currency_id
                )
            else:
                tax_cutoff_amount = tax_line["amount"]
            tax_line_ids.append(
                Command.create(
                    {
                        "tax_id": tax_line["id"],
                        "base": tax_line["base"],
                        "amount": tax_line["amount"],
                        "sequence": tax_line["sequence"],
                        "cutoff_account_id": tax_cutoff_account_id.id,
                        "cutoff_amount": tax_cutoff_amount,
                    },
                )
            )
            return tax_line_ids

    def _get_amount_company_currency(self, amount):
        self.ensure_one()
        if self.company_currency_id != self.currency_id:
            currency_at_date = self.currency_id.with_context(date=self.cutoff_date)
            amount_company_currency = currency_at_date.compute(
                amount, self.company_currency_id
            )
        else:
            amount_company_currency = amount
        return amount_company_currency

    @api.constrains("quantity")
    def _calc_cutoff_amount(self):

        for rec in self:
            if not rec.purchase_line_id and not rec.sale_line_id:
                continue
            amount = self._get_amount()
            tax_line_ids = self._get_tax_values()
            amount_company_currency = self._get_amount_company_currency(amount)
            rec.write(
                {
                    "amount": amount,
                    "cutoff_amount": amount_company_currency,
                    "tax_line_ids": tax_line_ids,
                }
            )

    def _get_cutoff_invoiced_qty(self):
        self.ensure_one()
        return sum(
            line.quantity
            for line in self.invoiced_qty_ids
            if line.move_id.state == "posted"
            and line.move_id.date <= self.parent_id.cutoff_date
        )

    def _add_move_line(self, move_line):
        self.ensure_one()
        if move_line.move_id.move_type in ("in_refund", "out_refund"):
            sign = -1
        else:
            sign = 1
        self.write(
            {
                "invoiced_qty_ids": [
                    Command.create(
                        {
                            "move_line_id": move_line.id,
                            "quantity": move_line.quantity * sign,
                        },
                    )
                ],
            }
        )
        self._update_quantity(move_line)

    def _update_quantity(self, move_line):
        self.ensure_one()
        if self.parent_id.cutoff_type == "accrued_revenue":
            quantity = sum(
                sol._get_cutoff_quantity(self._get_cutoff_invoiced_qty())
                for sol in move_line.sale_line_ids
            )
        else:
            quantity = move_line.purchase_line_id._get_cutoff_quantity(
                self._get_cutoff_invoiced_qty()
            )
        self.quantity = quantity
