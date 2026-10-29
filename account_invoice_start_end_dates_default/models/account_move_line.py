# Copyright 2026 Lorenzo Battistini
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date(
        compute="_compute_start_end_dates",
        store=True,
        readonly=False,
        precompute=True,
        copy=False,
    )
    end_date = fields.Date(
        compute="_compute_start_end_dates",
        store=True,
        readonly=False,
        precompute=True,
        copy=False,
    )

    def _copy_data_extend_business_fields(self, values):
        # The dates refer to the period of the invoice: they are not copied
        # when an invoice is duplicated, because the copy is a new invoice with
        # a new date, but a credit note covers the period of the reversed
        # invoice, so its lines keep the dates.
        res = super()._copy_data_extend_business_fields(values)
        values["start_date"] = self.start_date
        values["end_date"] = self.end_date
        return res

    @api.depends("move_id.invoice_date", "display_type")
    def _compute_start_end_dates(self):
        # The invoice date is only a default: we never overwrite dates that are
        # already set on the line, so that the user can enter another period.
        # The company options are deliberately not dependencies, otherwise
        # enabling them would fill the lines of all the existing invoices.
        for line in self:
            move = line.move_id
            company = move.company_id
            use_invoice_date = (
                move.is_purchase_document(include_receipts=True)
                and company.start_end_dates_from_bill_date
            ) or (
                move.is_sale_document(include_receipts=True)
                and company.start_end_dates_from_invoice_date
            )
            if (
                use_invoice_date
                and line.display_type == "product"
                and not line.start_date
                and not line.end_date
                and move.invoice_date
            ):
                line.start_date = move.invoice_date
                line.end_date = move.invoice_date
