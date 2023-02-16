# Copyright 2013-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import format_date, format_datetime, formatLang


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    picking_interval_days = fields.Integer(
        string="Analysis Interval",
        default=lambda self: self._default_picking_interval_days(),
        help="To generate the accrual/prepaid revenue/expenses based on picking "
        "dates vs invoice dates, Odoo will analyse all the pickings/invoices from "
        "N days before the cutoff date up to the cutoff date. "
        "N is the Analysis Interval. If you increase the analysis interval, "
        "Odoo will take more time to generate the cutoff lines.",
    )

    _sql_constraints = [
        (
            "picking_interval_days_positive",
            "CHECK(picking_interval_days > 0)",
            "The value of the field 'Analysis Interval' must be strictly positive.",
        )
    ]

    @api.model
    def _default_picking_interval_days(self):
        return self.env.company.default_cutoff_accrual_picking_interval_days

    def picking_prepare_cutoff_line(self, vdict, account_mapping):
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        if self.cutoff_type in ("accrued_expense", "accrued_revenue"):
            qty = vdict["precut_delivered_qty"] - vdict["precut_invoiced_qty"]
            qty_label = _("Pre-cutoff delivered quantity minus invoiced quantity:")
        elif self.cutoff_type in ("prepaid_expense", "prepaid_revenue"):
            qty = vdict["precut_invoiced_qty"] - vdict["precut_delivered_qty"]
            qty_label = _("Pre-cutoff invoiced quantity minus delivered quantity:")

        if float_compare(qty, 0, precision_digits=qty_prec) <= 0:
            return False

        company_currency = self.company_currency_id
        currency = vdict["currency"]
        sign = self.cutoff_type in ("accrued_expense", "prepaid_revenue") and -1 or 1
        amount = qty * vdict["price_unit"] * sign
        amount_company_currency = vdict["currency"]._convert(
            amount, company_currency, self.company_id, self.cutoff_date
        )

        # Use account mapping
        account_id = vdict["account_id"]
        if account_id in account_mapping:
            cutoff_account_id = account_mapping[account_id]
        else:
            cutoff_account_id = account_id
        uom_name = vdict["product"].uom_id.name
        notes = vdict["notes"]
        precut_delivered_qty_fl = formatLang(
            self.env, vdict.get("precut_delivered_qty", 0), dp="Product Unit of Measure"
        )
        notes += (
            "\n"
            + _("Pre-cutoff delivered quantity:")
            + " %s %s"
            % (
                precut_delivered_qty_fl,
                uom_name,
            )
        )
        if vdict.get("precut_delivered_logs"):
            notes += (
                "\n"
                + _("Pre-cutoff delivered quantity details:")
                + "\n%s" % "\n".join(vdict["precut_delivered_logs"])
            )
        precut_invoiced_qty_fl = formatLang(
            self.env, vdict.get("precut_invoiced_qty", 0), dp="Product Unit of Measure"
        )
        notes += (
            "\n"
            + _("Pre-cutoff invoiced quantity:")
            + " %s %s" % (precut_invoiced_qty_fl, uom_name)
        )
        if vdict.get("precut_invoiced_logs"):
            notes += (
                "\n"
                + _("Pre-cutoff invoiced quantity details:")
                + "\n%s" % "\n".join(vdict["precut_invoiced_logs"])
            )
        qty_fl = formatLang(self.env, qty, dp="Product Unit of Measure")
        notes += "\n%s %s %s" % (qty_label, qty_fl, uom_name)

        vals = {
            "parent_id": self.id,
            "partner_id": vdict["partner"].id,
            "name": vdict["name"],
            "account_id": account_id,
            "cutoff_account_id": cutoff_account_id,
            "analytic_account_id": vdict["analytic_account_id"],
            "currency_id": vdict["currency"].id,
            "quantity": qty,
            "price_unit": vdict["price_unit"],
            "amount": amount,
            "cutoff_amount": amount_company_currency,
            "price_origin": vdict.get("price_origin"),
            "notes": notes,
        }

        if (
            self.cutoff_type in ("accrued_expense", "accrued_revenue")
            and vdict["taxes"]
            and self.company_id.accrual_taxes
        ):
            # vdict["price_unit"] is a price without tax,
            # so I set handle_price_include=False
            tax_compute_all_res = vdict["taxes"].compute_all(
                vdict["price_unit"],
                currency=currency,
                quantity=qty * sign,
                product=vdict["product"],
                partner=vdict["partner"],
                handle_price_include=False,
            )
            vals["tax_line_ids"] = self._prepare_tax_lines(
                tax_compute_all_res, self.company_currency_id
            )
        return vals

    def order_line_update_oline_dict(
        self, order_line, order_type, oline_dict, cutoff_datetime
    ):
        assert order_line not in oline_dict
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        # These fields have the same name on PO and SO
        order = order_line.order_id
        product = order_line.product_id
        product_uom = product.uom_id
        moves = order_line.move_ids
        if self.source_move_state == "posted":
            ilines = order_line.invoice_lines.filtered(
                lambda x: x.parent_state == "posted"
            )
        else:
            ilines = order_line.invoice_lines.filtered(
                lambda x: x.parent_state in ("draft", "posted")
            )
        oline_dict[order_line] = {
            "precut_delivered_qty": 0.0,  # in product_uom
            "precut_delivered_logs": [],
            "precut_invoiced_qty": 0.0,  # in product_uom
            "precut_invoiced_logs": [],
            "name": _("%s: %s") % (order.name, order_line.name),
            "product": product,
            "partner": order.partner_id.commercial_partner_id,
            "notes": "",
            "price_unit": 0.0,
            "price_origin": False,
            "currency": False,
            "analytic_account_id": False,
            "account_id": False,
            "taxes": False,
        }
        wdict = oline_dict[order_line]
        if order_type == "purchase":
            ordered_qty = order_line.product_uom._compute_quantity(
                order_line.product_qty, product_uom
            )
            wdict["notes"] = _(
                "Purchase order %s confirmed on %s\n"
                "Purchase Order Line: %s (ordered qty: %s %s)"
            ) % (
                order.name,
                format_datetime(self.env, order.date_approve),
                order_line.name,
                formatLang(self.env, ordered_qty, dp="Product Unit of Measure"),
                product_uom.name,
            )
        elif order_type == "sale":
            ordered_qty = order_line.product_uom._compute_quantity(
                order_line.product_uom_qty, product_uom
            )
            wdict["notes"] = _(
                "Sale order %s confirmed on %s\n"
                "Sale Order Line: %s (ordered qty: %s %s)"
            ) % (
                order.name,
                format_datetime(self.env, order.date_order),
                order_line.name,
                formatLang(self.env, ordered_qty, dp="Product Unit of Measure"),
                product_uom.name,
            )
        for move in moves:
            if move.state == "done" and move.date <= cutoff_datetime:
                sign = 0
                if (
                    move.location_id.usage != "internal"
                    and move.location_dest_id.usage == "internal"
                ):
                    # purchase: regular move ; sale: reverse move
                    sign = order_type == "purchase" and 1 or -1
                elif (
                    move.location_id.usage == "internal"
                    and move.location_dest_id.usage != "internal"
                ):
                    # purchase: reverse move ; sale: regular move
                    sign = order_type == "sale" and 1 or -1
                if sign:
                    move_qty = move.product_uom._compute_quantity(
                        move.quantity_done * sign, product_uom
                    )
                    wdict["precut_delivered_qty"] += move_qty
                    move_qty_formatted = formatLang(
                        self.env, move_qty, dp="Product Unit of Measure"
                    )
                    wdict["precut_delivered_logs"].append(
                        " • %s %s (picking %s transfered on %s from %s to %s)"
                        % (
                            move_qty_formatted,
                            move.product_id.uom_id.name,
                            move.picking_id.name or "none",
                            format_datetime(self.env, move.date),
                            move.location_id.display_name,
                            move.location_dest_id.display_name,
                        )
                    )

        move_type2label = dict(
            self.env["account.move"].fields_get("move_type", "selection")["move_type"][
                "selection"
            ]
        )
        for iline in ilines:
            invoice = iline.move_id
            if not float_is_zero(iline.quantity, precision_digits=qty_prec):
                sign = invoice.move_type in ("out_refund", "in_refund") and -1 or 1
                iline_qty_puom = iline.product_uom_id._compute_quantity(
                    iline.quantity * sign, product_uom
                )
                if invoice.date <= self.cutoff_date:
                    wdict["precut_invoiced_qty"] += iline_qty_puom
                    iline_qty_puom_formatted = formatLang(
                        self.env, iline_qty_puom, dp="Product Unit of Measure"
                    )
                    wdict["precut_invoiced_logs"].append(
                        " • %s %s (%s %s dated %s)"
                        % (
                            iline_qty_puom_formatted,
                            iline.product_id.uom_id.name,
                            move_type2label[invoice.move_type],
                            invoice.name,
                            format_date(self.env, invoice.date),
                        )
                    )
                # Most recent invoice line used for price_unit, account,...
                wdict["price_unit"] = iline.price_subtotal / iline_qty_puom
                wdict["price_origin"] = invoice.name
                wdict["currency"] = invoice.currency_id
                wdict["account_id"] = iline.account_id.id
                wdict["analytic_account_id"] = iline.analytic_account_id.id
                wdict["taxes"] = iline.tax_ids
        if not wdict["price_origin"]:
            self.order_line_update_oline_dict_price_fallback(
                order_line, order_type, oline_dict
            )

    def order_line_update_oline_dict_price_fallback(
        self, order_line, order_type, oline_dict
    ):
        wdict = oline_dict[order_line]
        order = order_line.order_id
        product = order_line.product_id
        if order_type == "purchase":
            oline_qty_puom = order_line.product_uom._compute_quantity(
                order_line.product_qty, product.uom_id
            )
            wdict["price_unit"] = order_line.price_subtotal / oline_qty_puom
            wdict["price_origin"] = order.name
            wdict["currency"] = order.currency_id
            wdict["analytic_account_id"] = order_line.account_analytic_id.id
            wdict["taxes"] = order_line.taxes_id
            account = product._get_product_accounts()["expense"]
            if not account:
                raise UserError(
                    _(
                        "Missing expense account on product '%s' or on its "
                        "related product category '%s'."
                    )
                    % (product.display_name, product.categ_id.display_name)
                )
            wdict["account_id"] = order.fiscal_position_id.map_account(account).id
        elif order_type == "sale":
            oline_qty_puom = order_line.product_uom._compute_quantity(
                order_line.product_uom_qty, product.uom_id
            )
            wdict["price_unit"] = order_line.price_subtotal / oline_qty_puom
            wdict["price_origin"] = order.name
            wdict["currency"] = order.currency_id
            wdict["analytic_account_id"] = order.analytic_account_id.id
            wdict["taxes"] = order_line.tax_id
            account = product._get_product_accounts()["income"]
            if not account:
                raise UserError(
                    _(
                        "Missing income account on product '%s' or on its "
                        "related product category '%s'."
                    )
                    % (product.display_name, product.categ_id.display_name)
                )
            wdict["account_id"] = order.fiscal_position_id.map_account(account).id

    def stock_move_update_oline_dict(self, move_line, oline_dict, cutoff_datetime):
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        if self.cutoff_type == "accrued_expense":
            if (
                move_line.purchase_line_id
                and move_line.purchase_line_id not in oline_dict
                and not float_is_zero(
                    move_line.purchase_line_id.product_qty, precision_digits=qty_prec
                )
            ):
                self.order_line_update_oline_dict(
                    move_line.purchase_line_id, "purchase", oline_dict, cutoff_datetime
                )
        elif self.cutoff_type == "accrued_revenue":
            if (
                move_line.sale_line_id
                and move_line.sale_line_id not in oline_dict
                and not float_is_zero(
                    move_line.sale_line_id.product_uom_qty, precision_digits=qty_prec
                )
            ):
                self.order_line_update_oline_dict(
                    move_line.sale_line_id, "sale", oline_dict, cutoff_datetime
                )

    def invoice_line_update_oline_dict(self, inv_line, oline_dict, cutoff_datetime):
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        if self.cutoff_type == "prepaid_expense":
            if (
                inv_line.purchase_line_id
                and inv_line.purchase_line_id not in oline_dict
                and not float_is_zero(
                    inv_line.purchase_line_id.product_qty, precision_digits=qty_prec
                )
            ):
                self.order_line_update_oline_dict(
                    inv_line.purchase_line_id, "purchase", oline_dict, cutoff_datetime
                )
        elif self.cutoff_type == "prepaid_revenue":
            for so_line in inv_line.sale_line_ids:
                if so_line not in oline_dict and not float_is_zero(
                    so_line.product_uom_qty, precision_digits=qty_prec
                ):
                    self.order_line_update_oline_dict(
                        so_line, "sale", oline_dict, cutoff_datetime
                    )

    def get_lines(self):
        res = super().get_lines()
        aclo = self.env["account.cutoff.line"]

        account_mapping = self._get_mapping_dict()
        cutoff_type = self.cutoff_type
        cutoff_datetime = self._get_cutoff_datetime()

        oline_dict = {}  # order line dict
        # key = PO line or SO line recordset
        # value = {
        #   'precut_delivered_qty': 1.0,
        #   'precut_invoiced_qty': 0.0,
        #   'price_unit': 12.42,
        #   }

        # ACCRUAL :
        # starting point : picking
        # then, go to order line. From order line, go to stock moves and invoices lines
        # => gen cutoff line if precut_delivered_qty - precut_invoiced_qty > 0
        # PREPAID :
        # starting point : invoice
        # then, go to order line. From order line, go to stock moves and invoices lines
        # => gen cutoff line if precut_invoiced_qty - precut_delivered_qty > 0

        # ACCURAL
        if cutoff_type in ("accrued_revenue", "accrued_expense"):
            pick_type_map = {
                "accrued_revenue": "outgoing",
                "accrued_expense": "incoming",
            }

            min_date_dt = cutoff_datetime - relativedelta(
                days=self.picking_interval_days
            )

            pickings = self.env["stock.picking"].search(
                [
                    ("picking_type_code", "=", pick_type_map[cutoff_type]),
                    ("state", "=", "done"),
                    ("date_done", "<=", cutoff_datetime),
                    ("date_done", ">=", min_date_dt),
                    ("company_id", "=", self.company_id.id),
                ]
            )

            for p in pickings:
                for move in p.move_lines.filtered(lambda m: m.state == "done"):
                    self.stock_move_update_oline_dict(move, oline_dict, cutoff_datetime)
        elif cutoff_type in ("prepaid_revenue", "prepaid_expense"):
            move_type_map = {
                "prepaid_revenue": ("out_invoice", "out_refund"),
                "prepaid_expense": ("in_invoice", "in_refund"),
            }
            min_date = self.cutoff_date - relativedelta(days=self.picking_interval_days)
            inv_domain = [
                ("move_type", "in", move_type_map[cutoff_type]),
                ("date", "<=", self.cutoff_date),
                ("date", ">=", min_date),
                ("company_id", "=", self.company_id.id),
            ]
            if self.source_move_state == "posted":
                inv_domain.append(("state", "=", "posted"))
            else:
                inv_domain.append(("state", "in", ("draft", "posted")))
            invoices = self.env["account.move"].search(inv_domain)
            for invoice in invoices:
                for iline in invoice.invoice_line_ids.filtered(
                    lambda x: not x.display_type
                    and x.product_id.type in ("product", "consu")
                ):
                    self.invoice_line_update_oline_dict(
                        iline, oline_dict, cutoff_datetime
                    )

        # from pprint import pprint
        # pprint(oline_dict)
        for vdict in oline_dict.values():
            vals = self.picking_prepare_cutoff_line(vdict, account_mapping)
            if vals:
                aclo.create(vals)
        return res

    def _get_cutoff_datetime(self):
        self.ensure_one()
        cutoff_date = datetime.combine(self.cutoff_date, datetime.max.time())
        tz = self.env.user.tz and pytz.timezone(self.env.user.tz) or pytz.utc
        cutoff_datetime_aware = tz.localize(cutoff_date)
        cutoff_datetime_utc = cutoff_datetime_aware.astimezone(pytz.utc)
        cutoff_datetime_utc_naive = cutoff_datetime_utc.replace(tzinfo=None)
        return cutoff_datetime_utc_naive
