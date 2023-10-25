# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountCutoff(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.cutoff_journal = cls.env["account.journal"].create(
            {
                "code": "cop0",
                "company_id": cls.company.id,
                "name": "Cutoff Journal Base",
                "type": "general",
            }
        )
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "Cutoff Base Account",
                "code": "ACB480000",
                "company_ids": [Command.set([cls.company.id])],
                "account_type": "liability_current",
            }
        )
        cls.line_account = cls.env["account.account"].create(
            {
                "name": "Base Account",
                "code": "ACB220000",
                "company_ids": [Command.set([cls.company.id])],
                "account_type": "liability_current",
            }
        )
        cls.company.write(
            {
                "default_cutoff_journal_id": cls.cutoff_journal.id,
                "default_accrued_expense_account_id": cls.cutoff_account.id,
                "default_accrued_revenue_account_id": cls.cutoff_account.id,
            }
        )

    def _create_cutoff(self, cutoff_type="accrued_revenue", cutoff_date=None):
        if cutoff_date is None:
            cutoff_date = fields.Date.today()
        cutoff = self.env["account.cutoff"].create(
            {
                "cutoff_type": cutoff_type,
                "company_id": self.company.id,
                "cutoff_date": cutoff_date,
                "cutoff_account_id": self.cutoff_account.id,
                "cutoff_journal_id": self.cutoff_journal.id,
            }
        )
        cutoff.line_ids = [
            Command.create(
                {
                    "parent_id": cutoff.id,
                    "account_id": self.line_account.id,
                    "cutoff_account_id": self.cutoff_account.id,
                    "cutoff_amount": 50,
                }
            )
        ]
        return cutoff

    def test_compute_cutoff_account_id(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        self.assertEqual(cutoff.cutoff_account_id, self.cutoff_account)
        cutoff2 = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_revenue",
            }
        )
        self.assertEqual(cutoff2.cutoff_account_id, self.cutoff_account)

    def test_create_move_no_auto_reverse(self):
        """create_move without auto_reverse creates no reversal entry"""
        self.company.post_cutoff_move = False
        cutoff = self._create_cutoff()
        cutoff.auto_reverse = False
        cutoff.create_move()
        self.assertTrue(cutoff.move_id)
        self.assertEqual(cutoff.move_id.state, "draft")
        self.assertFalse(cutoff.move_reversal_id)

    def test_create_move_auto_reverse(self):
        """create_move with auto_reverse creates a reversal dated the next day"""
        self.company.post_cutoff_move = False
        cutoff_date = fields.Date.today()
        cutoff = self._create_cutoff(cutoff_date=cutoff_date)
        cutoff.auto_reverse = True
        cutoff.create_move()
        self.assertTrue(cutoff.move_id)
        self.assertEqual(cutoff.move_id.state, "draft")
        self.assertTrue(cutoff.move_reversal_id)
        self.assertEqual(cutoff.move_reversal_id.state, "draft")
        expected_reversal_date = cutoff_date + relativedelta(days=1)
        self.assertEqual(cutoff.move_reversal_id.date, expected_reversal_date)

    def test_create_move_auto_reverse_posted(self):
        """With post_cutoff_move=True, both move and reversal are posted"""
        self.company.post_cutoff_move = True
        cutoff = self._create_cutoff()
        cutoff.auto_reverse = True
        cutoff.create_move()
        self.assertEqual(cutoff.move_id.state, "posted")
        self.assertEqual(cutoff.move_reversal_id.state, "posted")

    def test_back2draft_clears_reversal(self):
        """back2draft unlinks the move and clears the computed reversal field"""
        self.company.post_cutoff_move = False
        cutoff = self._create_cutoff()
        cutoff.auto_reverse = True
        cutoff.create_move()
        self.assertTrue(cutoff.move_reversal_id)
        cutoff.back2draft()
        self.assertFalse(cutoff.move_id)
        self.assertFalse(cutoff.move_reversal_id)
