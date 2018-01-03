# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestAccountCutoff(SavepointCase):

    def test_default_cutoff_account_id(self):
        account_id = \
            self.env['account.cutoff']._default_cutoff_account_id()

        self.assertIsNone(account_id, 'The account must be none')
