# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import SavepointCase


@tagged("-at_install", "post_install")
class NoCuttOfInBankJournal(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_cutoff = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_current_liabilities").id,
                ),
                ("company_id", "=", cls.env.ref("base.main_company").id),
            ],
            limit=1,
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("code", "=", "BNK1")], limit=1
        )
        cls.miscellaneous_journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("code", "=", "MISC")], limit=1
        )
        cls.env.company.revenue_cutoff_journal_id = cls.miscellaneous_journal.id
        cls.env.company.expense_cutoff_journal_id = cls.miscellaneous_journal.id

    def test_no_cutoff_in_bank_journal(self):
        # here we wants to test the weird case where account deferred_accrual_account_id
        # would be set but as bank journal we could not determin proper journal to use
        self.bank_journal.default_account_id.deferred_accrual_account_id = (
            self.account_cutoff
        )
        partner = self.env.ref("base.res_partner_2")
        entry = self.env["account.move"].create(
            {
                "date": "2023-01-15",
                "move_type": "entry",
                "partner_id": partner.id,
                "journal_id": self.bank_journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "some amounts with date defined",
                            "debit": 2400,
                            "credit": 0,
                            "account_id": self.bank_journal.default_account_id.id,
                            "start_date": "2023-01-07",
                            "end_date": "2023-03-25",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "some amounts with date defined",
                            "debit": 0,
                            "credit": 2400,
                            "account_id": partner.property_account_receivable_id.id,
                            "start_date": "2023-01-07",
                            "end_date": "2023-03-25",
                        },
                    ),
                ],
            }
        )
        entry.action_post()
        # call it directly as entry are currently not supported !
        entry._create_cutoff_entries(
            entry.line_ids.filtered(lambda line: line.deferred_accrual_account_id)
        )
        self.assertEqual(entry.cutoff_move_count, 0)
        # in case other module let other journal to generate cut-off
        # hard to say if it's revenue or expense test neutral references
        self.assertEqual(
            entry._get_deferred_titles(),
            (
                "Advance recognition of %s (%s)"
                % (
                    entry.name,
                    entry.date.strftime("%m %Y"),
                ),
                "Advance adjustment of %s (%s)"
                % (
                    entry.name,
                    entry.date.strftime("%m %Y"),
                ),
            ),
        )
