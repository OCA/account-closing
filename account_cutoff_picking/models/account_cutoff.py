# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from datetime import datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def _nextday_start_dt(self):
        """Convert the cutoff date into datetime as start of next day."""
        next_day = self.cutoff_date + timedelta(days=1)
        tz = self.env.company.partner_id.tz or "UTC"
        start_next_day = datetime.combine(
            next_day, time(0, 0, 0, 0, tzinfo=pytz.timezone(tz))
        )
        return start_next_day.replace(tzinfo=None)

    def _get_account(self, line, type_cutoff, fpos):
        if type_cutoff in "accrued_revenue":
            map_type = "income"
        else:
            map_type = "expense"
        account = line.product_id.product_tmpl_id.get_product_accounts(fpos)[map_type]
        if not account:
            raise UserError(
                _(
                    "Error: Missing {map_type} account on product '{product}' or on"
                    " related product category.",
                ).format(
                    map_type=map_type,
                    product=line.product_id.name,
                )
            )
        return account

    def _get_partner(self, line):
        if self.cutoff_type == "accrued_expense":
            return line.order_id.partner_id
        return line.order_id.partner_invoice_id

    def _get_price_unit(self, line):
        if line.product_uom_qty:
            return line.price_subtotal / line.product_uom_qty
        if self.cutoff_type == "accrued_expense":
            return line.price_unit
        return line.price_reduce

    def _prepare_line(self, line):
        """
        Calculate accrued expense using purchase.order.line
        or accrued revenu using sale.order.line
        """
        self.ensure_one()
        if self.cutoff_type not in ("accrued_expense", "accrued_revenue"):
            return UserError(_("Wrong cutoff type %s") % self.cutoff_type)
        price_unit = self._get_price_unit(line)
        if not price_unit:
            return {}
        fpos = line.order_id.fiscal_position_id
        account_id = self._get_account(line, self.cutoff_type, fpos).id
        cutoff_account_id = self._get_mapping_dict().get(account_id, account_id)
        partner = self._get_partner(line)
        res = {
            "parent_id": self.id,
            "partner_id": partner.id,
            "name": line.name,
            "account_id": account_id,
            "cutoff_account_id": cutoff_account_id,
            "analytic_distribution": line.analytic_distribution,
            "currency_id": line.currency_id.id,
            "price_unit": price_unit,
        }
        if self.cutoff_type == "accrued_revenue":
            res["sale_line_id"] = line.id
        elif self.cutoff_type == "accrued_expense":
            res["purchase_line_id"] = line.id
        return res

    def _get_sale_lines_domain(self):
        domain = [("qty_to_invoice", "!=", 0)]
        if self.env.company.cutoff_exclude_locked_orders:
            domain.append(("order_id.state", "!=", "done"))
        return domain

    def _get_sale_lines(self):
        return self.env["sale.order.line"].search(self._get_sale_lines_domain())

    def _get_purchase_lines_domain(self):
        domain = [("qty_to_invoice", "!=", 0)]
        if self.env.company.cutoff_exclude_locked_orders:
            domain.append(("order_id.state", "!=", "done"))
        return domain

    def _get_purchase_lines(self):
        return self.env["purchase.order.line"].search(self._get_purchase_lines_domain())

    def _get_sale_extra_lines(self):
        # Take all moves done after the cutoff date
        cutoff_nextday = self._nextday_start_dt()
        moves_after = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("date", ">=", cutoff_nextday),
                ("sale_line_id", "!=", False),
            ],
            order="id",
        )
        sale_ids = set(moves_after.sale_line_id.order_id.ids)

        # Take all invoices impacting the cutoff
        # FIXME: what about ("move_id.payment_state", "=", "invoicing_legacy")
        domain = [
            ("move_id.move_type", "in", ("out_invoice", "out_refund")),
            ("sale_line_ids", "!=", False),
            "|",
            ("move_id.state", "=", "draft"),
            "&",
            ("move_id.state", "=", "posted"),
            ("move_id.date", ">=", cutoff_nextday),
        ]
        if self.env.company.cutoff_exclude_locked_orders:
            domain += [("sale_line_ids.order_id.state", "!=", "done")]
        invoice_line_after = self.env["account.move.line"].search(domain, order="id")
        _logger.debug(
            "Sales Invoice Lines done after cutoff: %s" % len(invoice_line_after)
        )
        sale_ids |= set(invoice_line_after.sale_line_ids.order_id.ids)
        sales = self.env["sale.order"].browse(sale_ids)
        return sales.order_line

    def _get_purchase_extra_lines(self):
        # Take all moves done after the cutoff date
        cutoff_nextday = self._nextday_start_dt()
        moves_after = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("date", ">=", cutoff_nextday),
                ("purchase_line_id", "!=", False),
            ],
            order="id",
        )
        _logger.debug("Moves done after cutoff: %s" % len(moves_after))
        purchase_ids = set(moves_after.purchase_line_id.order_id.ids)

        # Take all invoices impacting the cutoff
        # FIXME: what about ("move_id.payment_state", "=", "invoicing_legacy")
        domain = [
            ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ("purchase_line_id", "!=", False),
            "|",
            ("move_id.state", "=", "draft"),
            "&",
            ("move_id.state", "=", "posted"),
            ("move_id.date", ">=", cutoff_nextday),
        ]
        if self.env.company.cutoff_exclude_locked_orders:
            domain += [("purchase_line_id.order_id.state", "!=", "done")]
        invoice_line_after = self.env["account.move.line"].search(domain, order="id")
        _logger.debug(
            "Purchase Invoice Lines done after cutoff: %s" % len(invoice_line_after)
        )
        purchase_ids |= set(invoice_line_after.purchase_line_id.order_id.ids)
        purchases = self.env["purchase.order"].browse(purchase_ids)
        return purchases.order_line

    def _cleanup_lines(self):
        self.line_ids.unlink()

    def get_lines(self):
        self.ensure_one()
        # If the computation of the cutoff is done at the cutoff date, then we
        # only need to retrieve lines where there is a qty to invoice (i.e.
        # delivered qty != invoiced qty).
        # For any line where a move or an invoice has been done after the
        # cutoff date, we need to recompute the quantities.
        _logger.debug("Get lines")
        res = super().get_lines()
        if self.cutoff_type == "accrued_revenue":
            lines = self._get_sale_lines()
            extra_lines = self._get_sale_extra_lines()
            if extra_lines:
                lines |= extra_lines
        elif self.cutoff_type == "accrued_expense":
            lines = self._get_purchase_lines()
            _logger.debug("Lines to invoice found: %s" % len(lines))
            extra_lines = self._get_purchase_extra_lines()
            _logger.debug("Extra lines found: %s" % len(lines))
            if extra_lines:
                lines |= extra_lines
        else:
            return res

        _logger.debug("Prepare cutoff lines")
        values = []
        for line in lines:
            data = self._prepare_line(line)
            if data:
                values.append(data)
        self._create_cutoff_lines(values)
        return res

    def _create_cutoff_lines(self, values):
        _logger.debug("Filter %s cutoff lines" % len(values))
        values_to_create = []
        for val in values:
            acl = self.env["account.cutoff.line"].new(val)
            acl._compute_received_qty()
            acl._compute_invoiced_qty()
            if acl.quantity:
                # Save the computed values
                val.update(
                    {
                        "received_qty": acl.received_qty,
                        "invoiced_qty": acl.invoiced_qty,
                    }
                )
                values_to_create.append(val)
        self.env["account.cutoff.line"].create(values_to_create)

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
