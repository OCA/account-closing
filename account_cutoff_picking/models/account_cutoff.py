# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def _nextday_start_dt(self, date):
        """Convert a date into datetime as start of next day."""
        return self.cutoff_date + timedelta(days=1)

    def _get_account(self, line, type_cutoff, fpos):
        if type_cutoff in "accrued_revenue":
            map_type = "income"
        else:
            map_type = "expense"
        account = line.product_id.product_tmpl_id.get_product_accounts(fpos)[map_type]
        if not account:
            raise UserError(
                _(
                    "Error: Missing %(map_type)s account on product '%(product)s' or on"
                    " related product category.",
                    {"map_type": _(map_type), "product": line.product_id.name},
                )
            )
        return account

    def _get_partner(self, line):
        if self.cutoff_type == "accrued_expense":
            return line.order_id.partner_id
        return line.order_id.partner_invoice_id

    def _get_price_unit(self, line):
        if self.cutoff_type == "accrued_expense":
            return line.price_unit
        return line.price_reduce

    def _get_received_qty(self, line, cutoff_nextday):
        if self.cutoff_type == "accrued_expense":
            received_qty = line.qty_received
            # Processing purchase order line
            # The quantity received on the PO line must be deducted from all
            # moves done after the cutoff date.
            moves_after = line.move_ids.filtered(
                lambda r: r.state == "done" and r.date.date() >= cutoff_nextday
            )
            for move in moves_after:
                if move.product_uom != line.product_uom:
                    received_qty -= move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom
                    )
                else:
                    received_qty -= move.product_uom_qty
            return received_qty

        received_qty = line.qty_delivered
        # Processing sale order line
        # The quantity received on the SO line must be deducted from all
        # moves done after the cutoff date.
        moves_after = line.order_id.procurement_group_id.stock_move_ids.filtered(
            lambda r: r.state == "done" and r.date.date() >= cutoff_nextday
        )
        for move in moves_after:
            if move.product_uom != line.product_uom:
                received_qty -= move.product_uom._compute_quantity(
                    move.product_uom_qty, line.product_uom
                )
            else:
                received_qty -= move.product_uom_qty
        return received_qty

    def _prepare_line(self, line):
        """
        Calculate accrued expense using purchase.order.line.

        or accrued revenu using sale.order.line
        """
        assert self.cutoff_type in (
            "accrued_expense",
            "accrued_revenue",
        ), "The field 'type' has a wrong value"
        fpos = line.order_id.fiscal_position_id
        account_id = self._get_account(line, self.cutoff_type, fpos).id
        cutoff_account_id = self._get_mapping_dict().get(account_id, account_id)
        cutoff_nextday = self._nextday_start_dt(self.cutoff_date)
        received_qty = self._get_received_qty(line, cutoff_nextday)
        partner = self._get_partner(line)
        price_unit = self._get_price_unit(line)
        invoiced_qty = []
        invoiced_total_qty = 0.0
        for il in line.invoice_lines:
            if il.move_id.state != "posted" and not (
                il.move_id.state == "draft"
                and il.move_id.move_type == "in_refund"
                and il.move_id.create_date.date() < cutoff_nextday
            ):
                # Expense refunds are already accrued as credit notes to
                # We don't want here to accrue a quantity as goods to receive.
                continue
            if (il.move_id.date or il.move_id.invoice_date) <= self.cutoff_date:
                if il.move_id.move_type in ("in_refund", "out_refund"):
                    sign = -1
                else:
                    sign = 1
                invoiced_qty.append(
                    (
                        Command.create(
                            {"move_line_id": il.id, "quantity": il.quantity * sign}
                        ),
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
        quantity = line._get_cutoff_quantity(invoiced_total_qty)
        res = {
            "product_id": line.product_id.id,
            "parent_id": self.id,
            "partner_id": partner.id,
            "name": line.name,
            "account_id": account_id,
            "cutoff_account_id": cutoff_account_id,
            "analytic_distribution": line.analytic_distribution,
            "currency_id": line.currency_id.id,
            "price_unit": price_unit,
            "received_qty": received_qty,
            "invoiced_qty_ids": invoiced_qty,
            "quantity": quantity,
        }

        if self.cutoff_type == "accrued_revenue":
            res["sale_line_id"] = line.id
        elif self.cutoff_type == "accrued_expense":
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
                ("group_id.sale_id", "!=", False),
            ],
            order="id",
        )
        lines = moves_after.group_id.sale_id.order_line
        # Take all invoices done after the cutoff date
        invoices_after = self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "out_refund")),
                "|",
                ("date", ">", self.cutoff_date),
                "&",
                ("date", "=", False),
                ("invoice_date", ">", self.cutoff_date),
            ]
        )
        lines_invoices_after = invoices_after.mapped("invoice_line_ids.sale_line_ids")
        if lines_invoices_after:
            lines |= lines_invoices_after

        # Take all draft invoices
        invoices_draft = self.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("move_type", "in", ("out_invoice", "out_refund")),
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
        invoices_after = self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("move_type", "in", ("in_invoice", "in_refund")),
                "|",
                ("date", ">", self.cutoff_date),
                "&",
                ("date", "=", False),
                ("invoice_date", ">", self.cutoff_date),
            ]
        )
        lines_invoices_after = invoices_after.invoice_line_ids.purchase_line_id
        if lines_invoices_after:
            lines |= lines_invoices_after

        # Take all draft invoices
        invoices_draft = self.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("move_type", "in", ("in_invoice", "in_refund")),
            ]
        )
        lines_invoices_draft = invoices_draft.invoice_line_ids.purchase_line_id
        if lines_invoices_draft:
            lines |= lines_invoices_draft

        return lines

    def _cleanup_lines(self):
        self.line_ids.unlink()

    def get_lines(self):
        self.ensure_one()
        # If the computation of the cutoff is done at the cutoff date, then we
        # only need to retrieve lines where there is a qty to invoice (i.e.
        # delivered qty != invoiced qty).
        # For any line where a move or an invoice has been done after the
        # cutoff date, we need to recompute the quantities.
        res = super().get_lines()
        if self.cutoff_type == "accrued_revenue":
            lines = self._get_sale_lines()
            extra_lines = self._get_sale_extra_lines()
            if extra_lines:
                lines |= extra_lines
        elif self.cutoff_type == "accrued_expense":
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
        return res

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

    def _add_move_line(self, move_line):
        self.ensure_one()
        vals_list = []
        if self.cutoff_type == "accrued_revenue":
            for sol in move_line.sale_line_ids:
                vals = self._prepare_line(sol)
                if vals:
                    vals_list.append(vals)
        elif self.cutoff_type == "accrued_expense":
            vals = self._prepare_line(move_line.purchase_line_id)
            if vals:
                vals_list.append(vals)
        self.env["account.cutoff.line"].create(vals_list)
