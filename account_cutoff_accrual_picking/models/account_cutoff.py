# Copyright 2013-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    picking_interval_days = fields.Integer(
        string="Picking Analysis Interval",
        default=lambda self: self._default_picking_interval_days(),
        help="To generate the accruals based on pickings, Odoo will "
        "analyse all the pickings between the cutoff date and N "
        "days before. N is the Picking Analysis Interval.",
    )

    _sql_constraints = [
        (
            "picking_interval_days_positive",
            "CHECK(picking_interval_days > 0)",
            "The value of the field 'Picking Analysis Interval' must "
            "be strictly positive.",
        )
    ]

    @api.model
    def _default_picking_interval_days(self):
        return self.env.company.default_cutoff_accrual_picking_interval_days

    def picking_prepare_cutoff_line(self, vdict, account_mapping):
        dpo = self.env["decimal.precision"]
        assert self.cutoff_type in (
            "accrued_expense",
            "accrued_revenue",
        ), "The field 'cutoff_type' has a wrong value"
        qty_prec = dpo.precision_get("Product Unit of Measure")
        qty = vdict["precut_delivered_qty"] - vdict["precut_invoiced_qty"]
        if float_is_zero(qty, precision_digits=qty_prec):
            return False

        company_currency = self.company_currency_id
        currency = vdict["currency"]
        sign = self.cutoff_type == "accrued_expense" and -1 or 1
        amount = qty * vdict["price_unit"] * sign
        amount_company_currency = vdict["currency"]._convert(
            amount, company_currency, self.company_id, self.cutoff_date
        )

        # Use account mapping
        account_id = vdict["account_id"]
        if account_id in account_mapping:
            accrual_account_id = account_mapping[account_id]
        else:
            accrual_account_id = account_id
        vals = {
            "parent_id": self.id,
            "partner_id": vdict["partner"].id,
            "name": vdict["name"],
            "account_id": account_id,
            "cutoff_account_id": accrual_account_id,
            "analytic_account_id": vdict["analytic_account_id"],
            "currency_id": vdict["currency"].id,
            "quantity": qty,
            "price_unit": vdict["price_unit"],
            "amount": amount,
            "cutoff_amount": amount_company_currency,
            "price_origin": vdict.get("price_origin"),
        }

        if vdict["taxes"] and self.company_id.accrual_taxes:
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

    def order_line_update_oline_dict(self, order_line, order_type, oline_dict):
        assert order_line not in oline_dict
        dpo = self.env["decimal.precision"]
        qty_prec = dpo.precision_get("Product Unit of Measure")
        # These fields have the same name on PO and SO
        order = order_line.order_id
        product = order_line.product_id
        product_uom = product.uom_id
        moves = order_line.move_ids
        ilines = order_line.invoice_lines
        oline_dict[order_line] = {
            "precut_delivered_qty": 0.0,  # in product_uom
            "precut_invoiced_qty": 0.0,  # in product_uom
            "name": _(
                "%(order_name)s: %(order_line_name)s",
                order_name=order.name,
                order_line_name=order_line.name,
            ),
            "product": product,
            "partner": order.partner_id.commercial_partner_id,
        }
        if order_type == "purchase":
            invoice_type = "in_invoice"
        elif order_type == "sale":
            invoice_type = "out_invoice"
        for move in moves:
            # TODO: improve comparaison of date and datetime
            # for our friends far away from GMT
            if move.state == "done" and move.date.date() <= self.cutoff_date:
                move_qty = move.product_uom._compute_quantity(
                    move.product_uom_qty, product_uom
                )
                oline_dict[order_line]["precut_delivered_qty"] += move_qty
        price_origin = False
        for iline in ilines:
            invoice = iline.move_id
            if (
                invoice.move_type == invoice_type
                and float_compare(iline.quantity, 0, precision_digits=qty_prec) > 0
            ):
                iline_qty_puom = iline.product_uom_id._compute_quantity(
                    iline.quantity, product_uom
                )
                if invoice.date <= self.cutoff_date:
                    oline_dict[order_line]["precut_invoiced_qty"] += iline_qty_puom
                # Most recent invoice line used for price_unit, account,...
                price_unit = iline.price_subtotal / iline_qty_puom
                price_origin = invoice.name
                currency = invoice.currency_id
                account_id = iline.account_id.id
                analytic_account_id = iline.analytic_account_id.id
                taxes = iline.tax_ids
        if not price_origin:
            if order_type == "purchase":
                oline_qty_puom = order_line.product_uom._compute_quantity(
                    order_line.product_qty, product_uom
                )
                price_unit = order_line.price_subtotal / oline_qty_puom
                price_origin = order.name
                currency = order.currency_id
                analytic_account_id = order_line.account_analytic_id.id
                taxes = order_line.taxes_id
                account = product._get_product_accounts()["expense"]
                if not account:
                    raise UserError(
                        _(
                            "Missing expense account on product "
                            "'%(product_display_name)s' or on its "
                            "related product category '%(product_categ_display_name)s'.",
                            product_display_name=product.display_name,
                            product_categ_display_name=product.categ_id.display_name,
                        )
                    )
                account_id = order.fiscal_position_id.map_account(account).id
            elif order_type == "sale":
                oline_qty_puom = order_line.product_uom._compute_quantity(
                    order_line.product_uom_qty, product_uom
                )
                price_unit = order_line.price_subtotal / oline_qty_puom
                price_origin = order.name
                currency = order.currency_id
                analytic_account_id = order.analytic_account_id.id
                taxes = order_line.tax_id
                account = product._get_product_accounts()["income"]
                if not account:
                    raise UserError(
                        _(
                            "Missing income account on product "
                            "'%(product_display_name)s' or on its "
                            "related product category '%(product_categ_display_name)s'.",
                            product_display_name=product.display_name,
                            product_categ_display_name=product.categ_id.display_name,
                        )
                    )
                account_id = order.fiscal_position_id.map_account(account).id

        oline_dict[order_line].update(
            {
                "price_unit": price_unit,
                "price_origin": price_origin,
                "currency": currency,
                "analytic_account_id": analytic_account_id,
                "account_id": account_id,
                "taxes": taxes,
            }
        )

    def stock_move_update_oline_dict(self, move_line, oline_dict):
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
                    move_line.purchase_line_id, "purchase", oline_dict
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
                    move_line.sale_line_id, "sale", oline_dict
                )

    def get_lines(self):
        res = super().get_lines()
        spo = self.env["stock.picking"]
        aclo = self.env["account.cutoff.line"]

        pick_type_map = {
            "accrued_revenue": "outgoing",
            "accrued_expense": "incoming",
        }
        cutoff_type = self.cutoff_type
        if cutoff_type not in pick_type_map:
            return res

        # Create account mapping dict
        account_mapping = self._get_mapping_dict()

        min_date_dt = self.cutoff_date - relativedelta(days=self.picking_interval_days)

        # TODO date_done is a Datetime field, so maybe we need more clever code
        # for our friends which are far away from GMT
        pickings = spo.search(
            [
                ("picking_type_code", "=", pick_type_map[cutoff_type]),
                ("state", "=", "done"),
                ("date_done", "<=", self.cutoff_date),
                ("date_done", ">=", min_date_dt),
                ("company_id", "=", self.company_id.id),
            ]
        )

        oline_dict = {}  # order line dict
        # key = PO line or SO line recordset
        # value = {
        #   'precut_delivered_qty': 1.0,
        #   'precut_invoiced_qty': 0.0,
        #   'price_unit': 12.42,
        #   }
        # -> we use precut_delivered_qty - precut_invoiced_qty
        for p in pickings:
            for move in p.move_lines.filtered(lambda m: m.state == "done"):
                self.stock_move_update_oline_dict(move, oline_dict)

        # from pprint import pprint
        # pprint(oline_dict)
        for vdict in oline_dict.values():
            vals = self.picking_prepare_cutoff_line(vdict, account_mapping)
            if vals:
                aclo.create(vals)
        return res
