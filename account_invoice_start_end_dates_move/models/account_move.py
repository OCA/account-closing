# Copyright 2023 Sergio Corato
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    start_date = fields.Date()
    end_date = fields.Date()

    @api.onchange("start_date", "end_date")
    def _onchange_dates(self):
        for line in self.line_ids.filtered(
            lambda x: self.company_id.apply_dates_all_lines
            or x.product_id.must_have_dates
        ):
            line.start_date = line.move_id.start_date
            line.end_date = line.move_id.end_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("product_id", "company_id", "display_type")
    def _onchange_product_id(self):
        for line in self:
            if (
                line.company_id.apply_dates_all_lines or line.product_id.must_have_dates
            ) and line.display_type not in (
                "line_section",
                "line_note",
            ):
                if line.move_id.start_date:
                    line.start_date = line.move_id.start_date
                if line.move_id.end_date:
                    line.end_date = line.move_id.end_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            invoice = self.env["account.move"].browse(vals.get("move_id")).exists()
            if (
                invoice.company_id.apply_dates_all_lines
                or vals.get("product_id")
                and self.env["product.product"]
                .browse(vals["product_id"])
                .exists()
                .must_have_dates
            ):
                if not vals.get("start_date", False):
                    if invoice.start_date:
                        vals["start_date"] = invoice.start_date
                if not vals.get("end_date", False):
                    if invoice.end_date:
                        vals["end_date"] = invoice.end_date
        return super().create(vals_list)
