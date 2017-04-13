# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from odoo.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):

    def test_inherit_default_cutoff_account_id(self):
        company = self.env.user.company_id
        default_accrued_expense_account_id = \
            company.default_accrued_expense_account_id.id or False
        default_accrued_revenue_account_id = \
            company.default_accrued_revenue_account_id.id or False

        account_id = \
            self.env['account.cutoff'].with_context(type='accrued_expense').\
            _inherit_default_cutoff_account_id()
        self.assertEqual(account_id, default_accrued_expense_account_id,
                         'The account must be equals to %s' %
                         default_accrued_expense_account_id)
        account_id = \
            self.env['account.cutoff'].with_context(type='accrued_revenue').\
            _inherit_default_cutoff_account_id()
        self.assertEqual(account_id, default_accrued_revenue_account_id,
                         'The account must be equals to %s' %
                         default_accrued_revenue_account_id)
