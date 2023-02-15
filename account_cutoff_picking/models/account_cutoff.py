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
        states={"done": [("readonly", True)]},
        tracking=True,
        help="To generate the cutoffs based on picking "
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
        return self.env.company.default_cutoff_picking_interval_days

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
            "analytic_distribution": vdict["analytic_distribution"],
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
        order = order_line.order_id  # same on PO and SO
        oline_dict[order_line] = {
            "precut_delivered_qty": 0.0,  # in product_uom
            "precut_delivered_logs": [],
            "precut_invoiced_qty": 0.0,  # in product_uom
            "precut_invoiced_logs": [],
            "name": ": ".join([order.name, order_line.name]),
            "product": order_line.product_id,
            "partner": order.partner_id.commercial_partner_id,
            "notes": "",
            "price_unit": 0.0,
            "price_origin": False,
            "currency": False,
            "analytic_distribution": False,
            "account_id": False,
            "taxes": False,
        }
        self.order_line_update_oline_dict_from_stock_moves(
            order_line, order_type, oline_dict, cutoff_datetime
        )
        self.order_line_update_oline_dict_from_invoice_lines(
            order_line, order_type, oline_dict, cutoff_datetime
        )
        if not oline_dict[order_line]["price_origin"]:
            self.order_line_update_oline_dict_price_fallback(
                order_line, order_type, oline_dict
            )

    def order_line_update_oline_dict_from_stock_moves(
        self, order_line, order_type, oline_dict, cutoff_datetime
    ):
        wdict = oline_dict[order_line]
        # These fields/methods have the same name on PO and SO
        order = order_line.order_id
        product = order_line.product_id
        product_uom = product.uom_id
        outgoing_moves, incoming_moves = order_line._get_outgoing_incoming_moves()
        if order_type == "purchase":
            ordered_qty = order_line.product_uom._compute_quantity(
                order_line.product_qty, product_uom
            )
            wdict["notes"] = _(
                "Purchase order %(order)s confirmed on %(confirm_date)s\n"
                "Purchase Order Line: %(order_line)s (ordered qty: %(qty)s %(uom)s)"
            ) % {
                "order": order.name,
                "confirm_date": format_datetime(self.env, order.date_approve),
                "order_line": order_line.name,
                "qty": formatLang(self.env, ordered_qty, dp="Product Unit of Measure"),
                "uom": product_uom.name,
            }
        elif order_type == "sale":
            ordered_qty = order_line.product_uom._compute_quantity(
                order_line.product_uom_qty, product_uom
            )
            wdict["notes"] = _(
                "Sale order %(order)s confirmed on %(confirm_date)s\n"
                "Sale Order Line: %(order_line)s (ordered qty: %(qty)s %(uom)s)"
            ) % {
                "order": order.name,
                "confirm_date": format_datetime(self.env, order.date_order),
                "order_line": order_line.name,
                "qty": formatLang(self.env, ordered_qty, dp="Product Unit of Measure"),
                "uom": product_uom.name,
            }
        move_logs = []
        for out_move in outgoing_moves.filtered(
            lambda m: m.state == "done" and m.date <= cutoff_datetime
        ):
            sign = order_type == "purchase" and -1 or 1
            move_qty = out_move.product_uom._compute_quantity(
                out_move.quantity_done * sign, product_uom
            )
            move_logs.append((out_move, move_qty))
        for in_move in incoming_moves.filtered(
            lambda m: m.state == "done" and m.date <= cutoff_datetime
        ):
            sign = order_type == "sale" and -1 or 1
            move_qty = in_move.product_uom._compute_quantity(
                in_move.quantity_done * sign, product_uom
            )
            move_logs.append((in_move, move_qty))
        move_logs_sorted = sorted(move_logs, key=lambda to_sort: to_sort[0].date)
        for (move, move_qty_signed) in move_logs_sorted:
            wdict["precut_delivered_qty"] += move_qty_signed
            move_qty_signed_formatted = formatLang(
                self.env, move_qty_signed, dp="Product Unit of Measure"
            )
            wdict["precut_delivered_logs"].append(
                _(
                    " • %(qty)s %(uom)s (picking %(picking)s transfered on %(date)s "
                    "from %(src_location)s to %(dest_location)s)"
                )
                % {
                    "qty": move_qty_signed_formatted,
                    "uom": move.product_id.uom_id.name,
                    "picking": move.picking_id.name or "none",
                    "date": format_datetime(self.env, move.date),
                    "src_location": move.location_id.display_name,
                    "dest_location": move.location_dest_id.display_name,
                }
            )

    def order_line_update_oline_dict_from_invoice_lines(
        self, order_line, order_type, oline_dict, cutoff_datetime
    ):
        wdict = oline_dict[order_line]
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        move_type2label = dict(
            self.env["account.move"].fields_get("move_type", "selection")["move_type"][
                "selection"
            ]
        )
        # These fields have the same name on PO and SO
        product = order_line.product_id
        product_uom = product.uom_id
        if self.source_move_state == "posted":
            ilines = order_line.invoice_lines.filtered(
                lambda x: x.parent_state == "posted"
            )
        else:
            ilines = order_line.invoice_lines.filtered(
                lambda x: x.parent_state in ("draft", "posted")
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
                        " • %(qty)s %(uom)s (%(move_type)s %(move_name)s dated %(date)s)"
                        % {
                            "qty": iline_qty_puom_formatted,
                            "uom": iline.product_id.uom_id.name,
                            "move_type": move_type2label[invoice.move_type],
                            "move_name": invoice.name,
                            "date": format_date(self.env, invoice.date),
                        }
                    )
                # Most recent invoice line used for price_unit, account,...
                wdict["price_unit"] = iline.price_subtotal / iline_qty_puom
                wdict["price_origin"] = invoice.name
                wdict["currency"] = invoice.currency_id
                wdict["account_id"] = iline.account_id.id
                wdict["analytic_distribution"] = iline.analytic_distribution
                wdict["taxes"] = iline.tax_ids

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
            wdict["analytic_distribution"] = order_line.analytic_distribution
            wdict["taxes"] = order_line.taxes_id
            account = product._get_product_accounts()["expense"]
            if not account:
                raise UserError(
                    _(
                        "Missing expense account on product '%(product)s' or on its "
                        "related product category '%(categ)s'."
                    )
                    % {
                        "product": product.display_name,
                        "categ": product.categ_id.display_name,
                    }
                )
            wdict["account_id"] = order.fiscal_position_id.map_account(account).id
        elif order_type == "sale":
            oline_qty_puom = order_line.product_uom._compute_quantity(
                order_line.product_uom_qty, product.uom_id
            )
            wdict["price_unit"] = order_line.price_subtotal / oline_qty_puom
            wdict["price_origin"] = order.name
            wdict["currency"] = order.currency_id
            wdict["analytic_distribution"] = order_line.analytic_distribution
            wdict["taxes"] = order_line.tax_id
            account = product._get_product_accounts()["income"]
            if not account:
                raise UserError(
                    _(
                        "Missing income account on product '%(product)s' or on its "
                        "related product category '%(categ)s'."
                    )
                    % {
                        "product": product.display_name,
                        "categ": product.categ_id.display_name,
                    }
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
                for move in p.move_ids.filtered(lambda m: m.state == "done"):
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
                    lambda x: x.display_type == "product"
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
