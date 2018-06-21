# -*- coding: utf-8 -*-
# Copyright 2017 Cédric Pigeon <cedric.pigeon@acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo import exceptions, fields


class TestAccountReversal(TransactionCase):

    def setUp(self):
        super(TestAccountReversal, self).setUp()
        self.company = self.env.ref('base.main_company')
        user_type_lia = self.env.ref(
            'account.data_account_type_current_liabilities')
        user_type_rec = self.env.ref(
            'account.data_account_type_receivable')
        user_type_rev = self.env.ref(
            'account.data_account_type_revenue')
        self.accrual_journal = self.env['account.journal'].create({
            'code': 'acc0',
            'company_id': self.company.id,
            'name': 'Accrual Journal 0',
            'type': 'general'})
        self.sale_journal = self.env['account.journal'].create({
            'code': 'sales0',
            'company_id': self.company.id,
            'name': 'Sales Journal 0',
            'type': 'sale'})
        self.accrual_account = self.env['account.account'].create({
            'name': 'Accrual account',
            'code': 'ACC480000',
            'company_id': self.company.id,
            'user_type_id': user_type_lia.id
        })
        self.sale_account = self.env['account.account'].create({
            'name': 'Sale account',
            'code': 'SA410000',
            'company_id': self.company.id,
            'user_type_id': user_type_rec.id,
            'reconcile': True,
        })
        self.rev_account = self.env['account.account'].create({
            'name': 'Revenue account',
            'code': 'REV410000',
            'company_id': self.company.id,
            'user_type_id': user_type_rev.id,
            'reconcile': True,
        })
        self.accrual_invoice = self.env['account.invoice'].create({
            'company_id': self.company.id,
            'partner_id': self.env.ref('base.res_partner_18').id,
            'journal_id': self.sale_journal.id,
            'state': 'draft',
            'type': 'out_invoice',
            'account_id': self.sale_account.id,
            'date_invoice': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Otpez Laptop without OS',
                'price_unit': 642,
                'quantity': 4,
                'account_id': self.rev_account.id})]
        })
        self.company.write({
            'default_accrued_revenue_account_id': self.accrual_account.id,
            'default_accrued_expense_account_id': self.accrual_account.id,
            'default_cutoff_journal_id': self.accrual_journal.id
        })

    def test_account_invoice_accrual_confirm(self):
        self.assertEqual(self.accrual_invoice.state, 'draft')

        accrual_wizard = self.env['account.move.accrue'].with_context(
            active_model='account.invoice',
            active_ids=[self.accrual_invoice.id]).create({})
        accrual_wizard.action_accrue()

        self.assertTrue(self.accrual_invoice.accrual_move_id)

        self.accrual_invoice.action_invoice_open()

        self.assertTrue(self.accrual_invoice.accrual_move_id.reversal_id)

        self.assertEqual(self.accrual_invoice.state, 'open')

        moves = self.env['account.move'].search(
            [('journal_id', '=', self.accrual_journal.id)])
        self.assertEqual(len(moves), 2)
        move1 = moves[0]
        move2 = moves[1]
        reverse = False
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        if move1.reversal_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_id.id)
        if move2.reversal_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_id.id)
        self.assertTrue(reverse)

    def test_account_invoice_accrual_remove(self):
        self.assertEqual(self.accrual_invoice.state, 'draft')

        accrual_wizard = self.env['account.move.accrue'].with_context(
            active_model='account.invoice',
            active_ids=[self.accrual_invoice.id]).create({})
        accrual_wizard.action_accrue()

        with self.assertRaises(exceptions.Warning):
            self.accrual_invoice.unlink()

        self.accrual_invoice.accrual_move_id.create_reversals()
        self.accrual_invoice.unlink()

        moves = self.env['account.move'].search(
            [('journal_id', '=', self.accrual_journal.id)])
        self.assertEqual(len(moves), 2)

        move1 = moves[0]
        move2 = moves[1]
        reverse = False
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        if move1.reversal_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_id.id)
        if move2.reversal_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_id.id)
        self.assertTrue(reverse)

    def test_account_invoice_reversal(self):
        self.assertEqual(self.accrual_invoice.state, 'draft')

        accrual_wizard = self.env['account.move.accrue'].with_context(
            active_model='account.invoice',
            active_ids=[self.accrual_invoice.id]).create({})
        accrual_wizard.action_accrue()

        reversal_wizard = self.env['account.move.reverse'].with_context(
            active_model='account.move',
            active_ids=[self.accrual_invoice.accrual_move_id.id]).create({})
        reversal_wizard.action_reverse()

        moves = self.env['account.move'].search(
            [('journal_id', '=', self.accrual_journal.id)])
        self.assertEqual(len(moves), 2)

        move1 = moves[0]
        move2 = moves[1]
        reverse = False
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        if move1.reversal_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_id.id)
        if move2.reversal_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_id.id)
        self.assertTrue(reverse)
