# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
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
                "company_id": cls.company.id,
                "account_type": "liability_current",
            }
        )

    def test_default_cutoff_account_id(self):
        account_id = self.env["account.cutoff"]._default_cutoff_account_id()
        self.assertEqual(account_id, False)

        company = self.env.company
        random_account = self.env["account.account"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if random_account:
            company.default_accrued_expense_account_id = random_account.id
            company.default_accrued_revenue_account_id = random_account.id

            account_id = (
                self.env["account.cutoff"]
                .with_context(default_cutoff_type="accrued_expense")
                ._default_cutoff_account_id()
            )
            self.assertEqual(
                account_id,
                random_account.id,
                "The account must be equals to %s" % random_account.id,
            )
            account_id = (
                self.env["account.cutoff"]
                .with_context(default_cutoff_type="accrued_revenue")
                ._default_cutoff_account_id()
            )
            self.assertEqual(
                account_id,
                random_account.id,
                "The account must be equals to %s" % random_account.id,
            )

    def test_create_move(self):
        type_cutoff = "accrued_revenue"
        cutoff = (
            self.env["account.cutoff"]
            .with_context(default_cutoff_type=type_cutoff)
            .create(
                {
                    "cutoff_type": type_cutoff,
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                    "cutoff_account_id": self.cutoff_account.id,
                    "cutoff_journal_id": self.cutoff_journal.id,
                }
            )
        )
        account = self.env["account.account"].create(
            {
                "name": "Base account",
                "code": "ACB220000",
                "company_id": self.company.id,
                "account_type": "liability_current",
            }
        )
        cutoff.line_ids = [
            Command.create(
                {
                    "parent_id": cutoff.id,
                    "account_id": account.id,
                    "cutoff_account_id": self.cutoff_account.id,
                    "cutoff_amount": 50,
                },
            )
        ]
        self.company.post_cutoff_move = False
        cutoff.auto_reverse = False
        cutoff.create_move()
        self.assertEqual(
            cutoff.move_id.state,
            "draft",
            "A draft move is expected",
        )
        self.assertFalse(
            cutoff.move_reversal_id,
            "No reversal move is expected",
        )
        cutoff.back2draft()
        self.assertFalse(
            cutoff.move_id,
            "No move is expected",
        )
        cutoff.auto_reverse = True
        cutoff.create_move()
        self.assertEqual(
            cutoff.move_id.state,
            "draft",
            "A draft move is expected",
        )
        self.assertEqual(
            cutoff.move_reversal_id.state,
            "draft",
            "A draft reversal move is expected",
        )
        cutoff.back2draft()
        self.assertFalse(
            cutoff.move_id,
            "No move is expected",
        )
        self.assertFalse(
            cutoff.move_reversal_id,
            "No reversal move is expected",
        )
        self.company.post_cutoff_move = True
        cutoff.create_move()
        self.assertEqual(
            cutoff.move_id.state,
            "posted",
            "A posted move is expected",
        )
        self.assertEqual(
            cutoff.move_id.state,
            "posted",
            "A posted reversal move is expected",
        )
