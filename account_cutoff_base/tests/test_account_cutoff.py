# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):

    def test_inherit_default_cutoff_account_id(self):
        account_id = \
            self.env['account.cutoff']._inherit_default_cutoff_account_id()

        self.assertIsNone(account_id, 'The account must be none')
