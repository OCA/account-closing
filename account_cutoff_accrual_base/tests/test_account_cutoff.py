# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):

    def setUp(self):
        super(TestAccountCutoff, self).setUp()

        company = self.env.user.company_id
        self.default_accrued_expense_account_id = \
            company.default_accrued_expense_account_id.id or False
        self.default_accrued_revenue_account_id = \
            company.default_accrued_revenue_account_id.id or False
        self.default_accrual_revenue_journal_id = \
            company.default_accrual_revenue_journal_id.id or False
        self.default_accrual_expense_journal_id = \
            company.default_accrual_expense_journal_id.id or False

    def test_inherit_default_cutoff_account_id(self):

        account_id = self.env['account.cutoff'].with_context(
            type='accrued_expense')._inherit_default_cutoff_account_id()
        self.assertEqual(account_id, self.default_accrued_expense_account_id,
                         'The account must be equals to %s' %
                         self.default_accrued_expense_account_id)
        account_id = self.env['account.cutoff'].with_context(
            type='accrued_revenue')._inherit_default_cutoff_account_id()

        self.assertEqual(account_id, self.default_accrued_revenue_account_id,
                         'The account must be equals to %s' %
                         self.default_accrued_revenue_account_id)

    def test_default_journal(self):

        journal_id = self.env['account.cutoff'].with_context(
            type='accrued_expense')._get_default_journal()
        self.assertEqual(journal_id, self.default_accrual_expense_journal_id,
                         'The account must be equals to %s' %
                         self.default_accrual_expense_journal_id)
        journal_id = self.env['account.cutoff'].with_context(
            type='accrued_revenue')._get_default_journal()
        self.assertEqual(journal_id, self.default_accrual_revenue_journal_id,
                         'The account must be equals to %s' %
                         self.default_accrual_revenue_journal_id)
