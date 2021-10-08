# -*- coding: utf-8 -*-
# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def _nextday_start_dt(self, date):
        """ Convert a date into datetime as start of next day """
        return fields.Datetime.to_string(
            fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(self.cutoff_date)
            )
            + timedelta(days=1)
        )

    @api.model
    def _inherit_default_cutoff_account_id(self):
        """ Set up default account for a new cutoff """
        account_id = super(AccountCutoff, self)._inherit_default_cutoff_account_id()
        type_cutoff = self.env.context.get("type")
        company = self.env.user.company_id
        if type_cutoff == "accrued_expense":
            account_id = company.default_accrued_expense_account_id.id or False
        elif type_cutoff == "accrued_revenue":
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    def _get_account_mapping(self):
        """ Prepare account mapping """
        return self.env["account.cutoff.mapping"]._get_mapping_dict(
            self.company_id.id, self.type
        )

    def _get_account(self, line, type_cutoff, fpos):
        if type_cutoff in "accrued_revenue":
            map_type = "income"
        else:
            map_type = "expense"
        account = line.product_id.product_tmpl_id.get_product_accounts(fpos)[map_type]
        if not account:
            raise UserError(
                _(
                    "Error: Missing %s account on product '%s' or on "
                    "related product category."
                )
                % (_(map_type), line.product_id.name)
            )
        return account

    def _prepare_line(self, line):
        """
        Calculate accrued expense using purchase.order.line
        or accrued revenu using sale.order.line
        """
        assert self.type in (
            "accrued_expense",
            "accrued_revenue",
        ), "The field 'type' has a wrong value"

        partner = line.order_id.partner_id
        fpos = partner.property_account_position_id
        account_id = self._get_account(line, self.type, fpos).id
        accrual_account_id = self._get_account_mapping().get(account_id, account_id)
        cutoff_nextday = self._nextday_start_dt(self.cutoff_date)

        if self.type == "accrued_expense":
            received_qty = line.qty_received
            # Processing purchase order line
            analytic_account_id = line.account_analytic_id.id
            price_unit = line.price_unit
            taxes = line.taxes_id
            taxes = fpos.map_tax(taxes)
            # The quantity received on the PO line must be deducted from all
            # moves done after the cutoff date.
            moves_after = line.move_ids.filtered(
                lambda r: r.state == "done" and r.date >= cutoff_nextday
            )
            for move in moves_after:
                if move.product_uom != line.product_uom:
                    received_qty -= move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom
                    )
                else:
                    received_qty -= move.product_uom_qty

        elif self.type == "accrued_revenue":
            received_qty = line.qty_delivered
            # Processing sale order line
            analytic_account_id = line.order_id.project_id.id or False
            price_unit = line.price_reduce
            taxes = line.tax_id
            taxes = fpos.map_tax(taxes)
            # The quantity received on the SO line must be deducted from all
            # moves done after the cutoff date.
            moves_after = line.procurement_ids.mapped("move_ids").filtered(
                lambda r: r.state == "done" and r.date >= cutoff_nextday
            )
            for move in moves_after:
                if move.product_uom != line.product_uom:
                    received_qty -= move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom
                    )
                else:
                    received_qty -= move.product_uom_qty

        invoiced_qty = []
        invoiced_total_qty = 0.0
        for il in line.invoice_lines:
            if il.invoice_id.state not in ("open", "paid") and not (
                il.invoice_id.state == "draft"
                and il.invoice_id.type == "in_refund"
                and il.invoice_id.create_date < cutoff_nextday
            ):
                # Expense refunds are already accrued as credit notes to
                # receive by the module account_invoice_accrual.
                # We don't want here to accrue a quantity as goods to receive.
                continue
            if (il.invoice_id.date or il.invoice_id.date_invoice) <= self.cutoff_date:
                if il.invoice_id.type in ("in_refund", "out_refund"):
                    sign = -1
                else:
                    sign = 1
                invoiced_qty.append(
                    (
                        0,
                        0,
                        {
                            "invoice_line_id": il.id,
                            "quantity": il.quantity * sign,
                        },
                    )
                )
                invoiced_total_qty += il.quantity * sign
        if (
            float_compare(
                invoiced_total_qty,
                received_qty,
                precision_rounding=line.product_uom.rounding,
            )
            == 0
        ):
            # The received and invoiced qty is equal, no entry to create
            return {}

        res = {
            "product_id": line.product_id.id,
            "parent_id": self.id,
            "partner_id": partner.id,
            "name": line.name,
            "account_id": account_id,
            "cutoff_account_id": accrual_account_id,
            "analytic_account_id": analytic_account_id,
            "currency_id": line.currency_id.id,
            "price_unit": price_unit,
            "tax_ids": [(6, 0, [tax.id for tax in taxes])],
            "received_qty": received_qty,
            "invoiced_qty_ids": invoiced_qty,
        }

        if self.type == "accrued_revenue":
            res["sale_line_id"] = line.id
        elif self.type == "accrued_expense":
            res["purchase_line_id"] = line.id

        return res

    def _get_sale_lines(self):
        return self.env["sale.order.line"].search([("qty_to_invoice", "!=", 0)])

    def _get_purchase_lines(self):
        return self.env["purchase.order.line"].search([("qty_to_invoice", "!=", 0)])

    def _get_sale_extra_lines(self):
        # Take all moves done after the cutoff date
        cutoff_nextday = self._nextday_start_dt(self.cutoff_date)
        moves_after = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("date", ">=", cutoff_nextday),
                ("procurement_id", "!=", False),
            ],
            order="id",
        )
        moves_after = moves_after.filtered(lambda m: m.procurement_id.sale_line_id)
        lines = moves_after.mapped("procurement_id.sale_line_id")

        # Take all invoices done after the cutoff date
        invoices_after = self.env["account.invoice"].search(
            [
                ("state", "in", ("open", "paid")),
                ("type", "in", ("out_invoice", "out_refund")),
                "|",
                ("date", ">", self.cutoff_date),
                "&",
                ("date", "=", False),
                ("date_invoice", ">", self.cutoff_date),
            ]
        )
        lines_invoices_after = invoices_after.mapped("invoice_line_ids.sale_line_ids")
        if lines_invoices_after:
            lines |= lines_invoices_after

        # Take all draft invoices
        invoices_draft = self.env["account.invoice"].search(
            [
                ("state", "=", "draft"),
                ("type", "in", ("out_invoice", "out_refund")),
            ]
        )
        lines_invoices_draft = invoices_draft.mapped("invoice_line_ids.sale_line_ids")
        if lines_invoices_draft:
            lines |= lines_invoices_draft

        return lines

    def _get_purchase_extra_lines(self):
        # Take all moves done after the cutoff date
        cutoff_nextday = self._nextday_start_dt(self.cutoff_date)
        moves_after = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("date", ">=", cutoff_nextday),
                ("purchase_line_id", "!=", False),
            ],
            order="id",
        )
        lines = moves_after.mapped("purchase_line_id")

        # Take all invoices done after the cutoff date
        invoices_after = self.env["account.invoice"].search(
            [
                ("state", "in", ("open", "paid")),
                ("type", "in", ("in_invoice", "in_refund")),
                "|",
                ("date", ">", self.cutoff_date),
                "&",
                ("date", "=", False),
                ("date_invoice", ">", self.cutoff_date),
            ]
        )
        lines_invoices_after = invoices_after.mapped(
            "invoice_line_ids.purchase_line_id"
        )
        if lines_invoices_after:
            lines |= lines_invoices_after

        # Take all draft invoices
        invoices_draft = self.env["account.invoice"].search(
            [
                ("state", "=", "draft"),
                ("type", "in", ("in_invoice", "in_refund")),
            ]
        )
        lines_invoices_draft = invoices_draft.mapped(
            "invoice_line_ids.purchase_line_id"
        )
        if lines_invoices_draft:
            lines |= lines_invoices_draft

        return lines

    def _cleanup_lines(self):
        self.line_ids.unlink()

    def get_lines(self):
        self.ensure_one()
        self._cleanup_lines()
        # If the computation of the cutoff is done at the cutoff date, then we
        # only need to retrieve lines where there is a qty to invoice (i.e.
        # delivered qty != invoiced qty).
        # For any line where a move or an invoice has been done after the
        # cutoff date, we need to recompute the quantities.
        res = super(AccountCutoff, self).get_lines()
        if self.type == "accrued_revenue":
            lines = self._get_sale_lines()
            extra_lines = self._get_sale_extra_lines()
            if extra_lines:
                lines |= extra_lines
        elif self.type == "accrued_expense":
            lines = self._get_purchase_lines()
            extra_lines = self._get_purchase_extra_lines()
            if extra_lines:
                lines |= extra_lines
        else:
            return res

        for line in lines:
            data = self._prepare_line(line)
            if data:
                self.env["account.cutoff.line"].create(data)

    @api.model
    def _cron_cutoff(self, type_cutoff):
        # Cron is expected to run at begin of new period. We need the last day
        # of previous month. Support some time difference and compute last day
        # of previous period.
        last_day = datetime.today()
        if last_day.day > 20:
            last_day += relativedelta(months=1)
        last_day = last_day.replace(day=1)
        last_day -= relativedelta(days=1)
        cutoff = self.with_context(type=type).create(
            {
                "cutoff_date": last_day,
                "type": type_cutoff,
                "auto_reverse": True,
            }
        )
        cutoff.get_lines()

    @api.model
    def _cron_cutoff_expense(self):
        self._cron_cutoff("accrued_expense")

    @api.model
    def _cron_cutoff_revenue(self):
        self._cron_cutoff("accrued_revenue")


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

    @api.constrains("quantity")
    def _calc_cutoff_amount(self):
        company = self.env.user.company_id
        for rec in self:
            if not rec.purchase_line_id and not rec.sale_line_id:
                continue
            tax_line_ids = [(5, 0, 0)]
            tax_res = rec.tax_ids.compute_all(
                rec.price_unit,
                rec.currency_id,
                rec.quantity,
                rec.product_id,
                rec.partner_id,
            )
            amount = tax_res["total_excluded"]
            if rec.parent_id.type == "accrued_expense":
                amount = amount * -1
                tax_account_field_name = "account_accrued_expense_id"
                tax_account_field_label = "Accrued Expense Tax Account"
            elif rec.parent_id.type == "accrued_revenue":
                tax_account_field_name = "account_accrued_revenue_id"
                tax_account_field_label = "Accrued Revenue Tax Account"
            for tax_line in tax_res["taxes"]:
                tax_read = rec.env["account.tax"].browse(tax_line["id"])
                tax_accrual_account_id = tax_read[tax_account_field_name]
                if not tax_accrual_account_id:
                    if not company.accrual_taxes:
                        continue
                    raise UserError(
                        _("Error: Missing '%s' on tax '%s'.")
                        % (tax_account_field_label, tax_read["name"])
                    )
                else:
                    tax_accrual_account_id = tax_accrual_account_id[0]
                if rec.parent_id.type == "accrued_expense":
                    tax_line["amount"] = tax_line["amount"] * -1
                if rec.company_currency_id != rec.currency_id:
                    currency_at_date = rec.currency_id.with_context(
                        date=rec.parent_id.cutoff_date
                    )
                    tax_accrual_amount = currency_at_date.compute(
                        tax_line["amount"], rec.company_currency_id
                    )
                else:
                    tax_accrual_amount = tax_line["amount"]
                tax_line_ids.append(
                    (
                        0,
                        0,
                        {
                            "tax_id": tax_line["id"],
                            "base": rec.env["res.currency"].round(
                                rec.price_unit * rec.quantity
                            ),
                            "amount": tax_line["amount"],
                            "sequence": tax_line["sequence"],
                            "cutoff_account_id": tax_accrual_account_id.id,
                            "cutoff_amount": tax_accrual_amount,
                            "analytic_account_id": tax_line["analytic"],
                            # tax_line['account_analytic_collected_id'],
                            # account_analytic_collected_id is for invoices IN and OUT
                        },
                    )
                )
            if rec.company_currency_id != rec.currency_id:
                currency_at_date = rec.currency_id.with_context(date=rec.cutoff_date)
                amount_company_currency = currency_at_date.compute(
                    amount, rec.company_currency_id
                )
            else:
                amount_company_currency = amount
            rec.write(
                {
                    "amount": amount,
                    "cutoff_amount": amount_company_currency,
                    "tax_line_ids": tax_line_ids,
                }
            )


class AccountCutoffLineInvoice(models.Model):
    _name = "account.cutoff.line.invoice"

    cutoff_line_id = fields.Many2one(
        "account.cutoff.line",
        "Cutoff Line",
        required=True,
        ondelete="cascade",
    )
    invoice_line_id = fields.Many2one(
        "account.invoice.line",
        "Invoice Line",
        required=True,
        ondelete="restrict",
    )
    invoice_id = fields.Many2one(related="invoice_line_id.invoice_id")
    quantity = fields.Float("Quantity")
