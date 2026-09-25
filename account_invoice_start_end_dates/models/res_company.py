# Copyright 2026 Lorenzo Battistini
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    start_end_dates_from_bill_date = fields.Boolean(
        string="Default Start/End Dates from Bill Date",
        help="If enabled, the lines of vendor bills and refunds that don't have "
        "a Start Date and an End Date get the bill date as Start Date and "
        "End Date.",
    )
    start_end_dates_from_invoice_date = fields.Boolean(
        string="Default Start/End Dates from Invoice Date",
        help="If enabled, the lines of customer invoices and refunds that don't "
        "have a Start Date and an End Date get the invoice date as Start Date "
        "and End Date.",
    )
