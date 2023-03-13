# Copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2023 Simone Rubino - TAKOBI
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time

from odoo import fields
from odoo.fields import first
from odoo.tests import tagged
from odoo.tests.common import SavepointCase, Form
from odoo.tools import float_compare


@tagged('-at_install', 'post_install')
class TestInvoiceStartEndDates(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inv_model = cls.env['account.invoice']
        cls.account_model = cls.env['account.account']
        cls.tax_model = cls.env['account.tax']
        cls.journal_model = cls.env['account.journal']
        cls.account_assets = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_current_assets').id)], limit=1)
        cls.account_revenue = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_revenue').id)], limit=1)
        cls.account_receivable = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_receivable').id)], limit=1)
        cls.cutoff_journal = cls.journal_model.search([], limit=1)
        cls.sale_journal = cls.journal_model.search([(
            'type', '=', 'sale')], limit=1)
        # enable grouping on sale journal
        cls.sale_journal.group_invoice_lines = True
        cls.maint_product = cls.env.ref(
            'account_invoice_start_end_dates.'
            'product_maintenance_contract_demo')
        cls.account_child_tax, cls.no_account_child_tax = cls.tax_model.create([
            {
                'name': "Child 8.8 Tax with Account",
                'account_id': cls.account_assets.id,
                'refund_account_id': cls.account_assets.id,
                'type_tax_use': 'none',
                'amount': 8.8,
                'amount_type': 'percent',
            },
            {
                'name': "Child 13.2 Tax without Account",
                'type_tax_use': 'none',
                'amount': 13.2,
                'amount_type': 'percent',
            },
        ])
        children_taxes = cls.account_child_tax + cls.no_account_child_tax
        cls.group_tax = cls.tax_model.create({
            'name': "Group 22 Tax",
            'type_tax_use': 'purchase',
            'amount': 22,
            'amount_type': 'group',
            'children_tax_ids': [(6, 0, children_taxes.ids)],
        })

    def _date(self, date):
        """ convert MM-DD to current year date YYYY-MM-DD """
        return time.strftime('%Y-' + date)

    def test_invoice_with_grouping(self):
        invoice = self.inv_model.create({
            'date_invoice': self._date('01-01'),
            'account_id': self.account_receivable.id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'journal_id': self.sale_journal.id,
            'type': 'out_invoice',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance IPBX 12 mois',
                    'price_unit': 2400,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('12-31'),
                    }),
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance téléphones 12 mois',
                    'price_unit': 12,
                    'quantity': 10,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('12-31'),
                    }),
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance Fax 6 mois',
                    'price_unit': 120.75,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('06-30'),
                    }),
                (0, 0, {
                    'product_id':
                    self.env.ref('product.product_product_5').id,
                    'name': 'HD IPBX',
                    'price_unit': 215.5,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    }),
                ],
        })
        invoice.action_invoice_open()
        self.assertTrue(invoice.move_id)
        iline_res = {
            (self._date('01-01'), self._date('12-31')): 2520,
            (self._date('01-01'), self._date('06-30')): 120.75,
            (False, False): 215.5,
            }
        precision = self.env['decimal.precision'].precision_get('Account')
        for mline in invoice.move_id.line_ids:
            if mline.account_id == self.account_revenue:
                amount = iline_res.pop(
                    (fields.Date.to_string(mline.start_date),
                     fields.Date.to_string(mline.end_date)))
                self.assertEquals(float_compare(
                    amount, mline.credit, precision_digits=precision), 0)

    def test_group_tax(self):
        """The move lines created from a group tax have dates
        only if the child tax has no account.
        """
        tax_start_date = self._date('01-01')
        tax_end_date = self._date('12-31')

        # Arrange: Create a vendor bill
        bill_model = self.inv_model.with_context(type='in_invoice')
        bill_form = Form(bill_model)
        bill_form.partner_id = self.env.ref('base.res_partner_1')
        with bill_form.invoice_line_ids.new() as line:
            line.name = "Test Group Tax"
            line.invoice_line_tax_ids.clear()
            line.invoice_line_tax_ids.add(self.group_tax)
            line.quantity = 1
            line.price_unit = 100
            line.start_date = tax_start_date
            line.end_date = tax_end_date
        bill = bill_form.save()
        # pre-condition: The line has a group tax,
        # one of the children has an account and the other does not
        group_tax = bill.invoice_line_ids.invoice_line_tax_ids
        self.assertEqual(group_tax.amount_type, 'group')
        children_taxes = group_tax.children_tax_ids
        account_child_tax = children_taxes.filtered('account_id')
        self.assertEqual(len(account_child_tax), 1)
        no_account_child_tax = children_taxes - account_child_tax
        self.assertEqual(len(no_account_child_tax), 1)

        # Act: Confirm the vendor bill
        bill.action_invoice_open()

        # Assert
        # The move line for the tax having an account has no dates
        bill_move_lines = bill.move_id.line_ids
        account_child_tax_lines = bill_move_lines.filtered(
            lambda l: l.tax_line_id == account_child_tax
        )
        self.assertTrue(account_child_tax_lines)
        self.assertFalse(account_child_tax_lines.start_date)
        self.assertFalse(account_child_tax_lines.end_date)

        # The move line for the tax having no account has the dates
        no_account_child_tax_lines = bill_move_lines.filtered(
            lambda l: l.tax_line_id == no_account_child_tax
        )
        self.assertTrue(no_account_child_tax_lines)
        self.assertEqual(
            fields.Date.to_string(no_account_child_tax_lines.start_date),
            tax_start_date,
        )
        self.assertEqual(
            fields.Date.to_string(no_account_child_tax_lines.end_date),
            tax_end_date,
        )

    def test_group_tax_multiple_dates(self):
        """If the invoice lines created from a group tax have different dates,
        their dates are propagated to the corresponding move lines.
        """
        first_start_date = self._date('01-01')
        second_start_date = self._date('02-02')
        second_end_date = self._date('03-03')
        first_end_date = self._date('12-31')

        # Arrange: Create a vendor bill
        group_tax = self.group_tax
        bill_model = self.inv_model.with_context(type='in_invoice')
        bill_form = Form(bill_model)
        bill_form.partner_id = self.env.ref('base.res_partner_1')
        with bill_form.invoice_line_ids.new() as line:
            line.name = "First Test line"
            line.invoice_line_tax_ids.clear()
            line.invoice_line_tax_ids.add(group_tax)
            line.quantity = 1
            line.price_unit = 100
            line.start_date = first_start_date
            line.end_date = first_end_date
        with bill_form.invoice_line_ids.new() as line:
            line.name = "Second test line"
            line.invoice_line_tax_ids.clear()
            line.invoice_line_tax_ids.add(group_tax)
            line.quantity = 1
            line.price_unit = 100
            line.start_date = second_start_date
            line.end_date = second_end_date
        bill = bill_form.save()
        # pre-condition: The lines have the same group tax but different dates
        self.assertEqual(
            bill.invoice_line_ids.mapped('invoice_line_tax_ids'),
            group_tax,
        )
        self.assertEqual(group_tax.amount_type, 'group')
        children_taxes = group_tax.children_tax_ids
        account_child_tax = children_taxes.filtered('account_id')
        self.assertEqual(len(account_child_tax), 1)
        no_account_child_tax = children_taxes - account_child_tax
        self.assertEqual(len(no_account_child_tax), 1)
        self.assertTrue(all(
            line.invoice_line_tax_ids == group_tax
            for line in bill.invoice_line_ids
        ))
        first_line = first(bill.invoice_line_ids)
        second_line = bill.invoice_line_ids - first_line
        self.assertTrue(
            first_line.start_date < second_line.start_date
            < second_line.end_date < first_line.end_date
        )

        # Act: Confirm the vendor bill
        bill.action_invoice_open()

        # Assert
        # The move line for the tax having an account has no dates
        bill_move = bill.move_id
        bill_move_lines = bill_move.line_ids
        account_child_tax_lines = bill_move_lines.filtered(
            lambda l: l.tax_line_id == account_child_tax
        )
        self.assertTrue(account_child_tax_lines)
        self.assertFalse(account_child_tax_lines.start_date)
        self.assertFalse(account_child_tax_lines.end_date)

        # The move lines for the tax having no account have the dates
        no_account_child_tax_lines = bill_move_lines.filtered(
            lambda l: l.tax_line_id == no_account_child_tax
        )
        first_move_tax_line = no_account_child_tax_lines.filtered(
            lambda l: l.start_date == fields.Date.to_date(first_start_date)
            and l.end_date == fields.Date.to_date(first_end_date)
        )
        self.assertTrue(first_move_tax_line)
        second_move_tax_line = no_account_child_tax_lines.filtered(
            lambda l: l.start_date == fields.Date.to_date(second_start_date)
            and l.end_date == fields.Date.to_date(second_end_date)
        )
        self.assertTrue(second_move_tax_line)

        # The bill and its move still have the same amount
        self.assertEqual(bill.amount_total, bill_move.amount)
