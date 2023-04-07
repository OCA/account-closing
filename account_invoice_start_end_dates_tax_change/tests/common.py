# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields

from odoo.addons.account_tax_change.tests.common import AccountTaxChangeCommon


class AccountTaxChangeStartEndDatesCommon(AccountTaxChangeCommon):
    at_install = False
    post_install = True

    @classmethod
    def _setup_invoice_dates(cls, change_date, start_date, end_date):
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        cls.tax_change_a2b.date = change_date
        cls.invoice_tax_a.invoice_line_ids.write(
            {"start_date": start_date, "end_date": end_date}
        )
        cls.invoice_tax_b.invoice_line_ids.write(
            {"start_date": start_date, "end_date": end_date}
        )
