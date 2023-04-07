# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields

from .common import AccountTaxChangeStartEndDatesCommon
from odoo.addons.account_invoice_start_end_dates_tax_change.wizards import (
    account_move_apply_tax_change as wiz
)


class TestAccountTaxChange(AccountTaxChangeStartEndDatesCommon):

    def test_apply_tax_change(self):
        """Apply a tax change A to B on an invoice using tax A."""
        self._setup_invoice_dates(
            change_date="2023-02-01",
            start_date="2023-01-01",
            end_date="2023-03-31",
        )
        invoice = self.invoice_tax_a
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        old_price_unit = invoice.invoice_line_ids.price_unit
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.apply_tax_change(self.tax_change_a2b, invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        line_from_start = invoice.invoice_line_ids.filtered(
            lambda l: l.end_date == self.tax_change_a2b.date
        )
        self.assertEqual(line_from_start.invoice_line_tax_ids, old_taxes)
        line_from_change = invoice.invoice_line_ids.filtered(
            lambda l: l.start_date == self.tax_change_a2b.date
        )
        new_taxes = line_from_change.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(
            line_from_start.price_unit + line_from_change.price_unit, old_price_unit
        )
        self.assertNotEqual(old_taxes, new_taxes)
        self.assertEqual(line_from_change.invoice_line_tax_ids, new_taxes)
        self.assertEqual(new_taxes, self.tax_sale_b)
        self.assertNotEqual(old_amount_tax, new_amount_tax)

    def test_apply_tax_change_no_change(self):
        """Change tax A to B on an invoice using already tax B."""
        invoice = self.invoice_tax_b
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        self.apply_tax_change(self.tax_change_a2b, invoice)
        new_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(old_taxes, new_taxes, self.tax_sale_b)
        self.assertEqual(old_amount_tax, new_amount_tax)

    def test_apply_tax_change_out_of_dates_no_change(self):
        """Change tax A to B on an invoice using tax A out of dates."""
        self._setup_invoice_dates(
            change_date="2025-05-01",
            start_date="2024-01-01",
            end_date="2024-02-29",
        )
        tax_change_date = fields.Date.from_string(self.tax_change_a2b.date)
        new_tax_change_date = wiz.date_subtract(tax_change_date, months=3)
        self.tax_change_a2b.date = fields.Date.to_string(new_tax_change_date)
        invoice = self.invoice_tax_a
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        self.apply_tax_change(self.tax_change_a2b, invoice)
        new_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(old_taxes, new_taxes, self.tax_sale_b)
        self.assertEqual(old_amount_tax, new_amount_tax)

    def test_apply_tax_change_on_2_months_period_in_leap_year(self):
        """Change tax A to B on invoice using tax A on 2 months period in leap year."""
        self._setup_invoice_dates(
            change_date="2024-02-01",
            start_date="2024-01-01",
            end_date="2024-02-29",
        )
        invoice = self.invoice_tax_a
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        old_price_unit = invoice.invoice_line_ids.price_unit
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.apply_tax_change(self.tax_change_a2b, invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        line_from_start = invoice.invoice_line_ids.filtered(
            lambda l: l.end_date == self.tax_change_a2b.date
        )
        self.assertEqual(line_from_start.invoice_line_tax_ids, old_taxes)
        line_from_change = invoice.invoice_line_ids.filtered(
            lambda l: l.start_date == self.tax_change_a2b.date
        )
        new_taxes = line_from_change.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(
            line_from_start.price_unit + line_from_change.price_unit, old_price_unit
        )
        self.assertNotEqual(old_taxes, new_taxes)
        self.assertEqual(line_from_change.invoice_line_tax_ids, new_taxes)
        self.assertEqual(new_taxes, self.tax_sale_b)
        self.assertNotEqual(old_amount_tax, new_amount_tax)

    def test_apply_tax_change_on_1_year_period_in_leap_year(self):
        """Change tax A to B on invoice using tax A on 2 months period in leap year."""
        self._setup_invoice_dates(
            change_date="2024-05-10",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        invoice = self.invoice_tax_a
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        old_price_unit = invoice.invoice_line_ids.price_unit
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.apply_tax_change(self.tax_change_a2b, invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        line_from_start = invoice.invoice_line_ids.filtered(
            lambda l: l.end_date == self.tax_change_a2b.date
        )
        self.assertEqual(line_from_start.invoice_line_tax_ids, old_taxes)
        line_from_change = invoice.invoice_line_ids.filtered(
            lambda l: l.start_date == self.tax_change_a2b.date
        )
        new_taxes = line_from_change.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(
            line_from_start.price_unit + line_from_change.price_unit, old_price_unit
        )
        self.assertNotEqual(old_taxes, new_taxes)
        self.assertEqual(line_from_change.invoice_line_tax_ids, new_taxes)
        self.assertEqual(new_taxes, self.tax_sale_b)
        self.assertNotEqual(old_amount_tax, new_amount_tax)

    def test_apply_tax_change_on_1_year_period_in_noleap_year(self):
        """Change tax A to B on invoice using tax A on 2 months period in noleap year."""
        self._setup_invoice_dates(
            change_date="2023-05-10",
            start_date="2023-01-01",
            end_date="2023-12-31",
        )
        invoice = self.invoice_tax_a
        old_taxes = invoice.invoice_line_ids.invoice_line_tax_ids
        old_amount_tax = invoice.amount_tax
        old_price_unit = invoice.invoice_line_ids.price_unit
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.apply_tax_change(self.tax_change_a2b, invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        line_from_start = invoice.invoice_line_ids.filtered(
            lambda l: l.end_date == self.tax_change_a2b.date
        )
        self.assertEqual(line_from_start.invoice_line_tax_ids, old_taxes)
        line_from_change = invoice.invoice_line_ids.filtered(
            lambda l: l.start_date == self.tax_change_a2b.date
        )
        new_taxes = line_from_change.invoice_line_tax_ids
        new_amount_tax = invoice.amount_tax
        self.assertEqual(
            line_from_start.price_unit + line_from_change.price_unit, old_price_unit
        )
        self.assertNotEqual(old_taxes, new_taxes)
        self.assertEqual(line_from_change.invoice_line_tax_ids, new_taxes)
        self.assertEqual(new_taxes, self.tax_sale_b)
        self.assertNotEqual(old_amount_tax, new_amount_tax)
