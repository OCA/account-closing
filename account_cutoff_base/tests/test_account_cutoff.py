# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
##############################################################################

from odoo.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):

    def test_default_cutoff_account_id(self):
        account_id = self.env['account.cutoff']._default_cutoff_account_id()

        self.assertIsNone(account_id, 'The account must be none')
