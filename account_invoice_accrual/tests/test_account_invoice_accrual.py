# Copyright 2017 Cédric Pigeon <cedric.pigeon@acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, exceptions, fields
from odoo.tests.common import TransactionCase


class TestAccountReversal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.accrual_journal = cls.env["account.journal"].create(
            {
                "code": "acc0",
                "company_id": cls.company.id,
                "name": "Accrual Journal 0",
                "type": "general",
            }
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "code": "sales0",
                "company_id": cls.company.id,
                "name": "Sales Journal 0",
                "type": "sale",
            }
        )
        cls.accrual_account = cls.env["account.account"].create(
            {
                "name": "Accrual account",
                "code": "ACC480000",
                "company_id": cls.company.id,
                "account_type": "liability_current",
            }
        )
        cls.rev_account = cls.env["account.account"].create(
            {
                "name": "Revenue account",
                "code": "REV410000",
                "company_id": cls.company.id,
                "account_type": "income",
                "reconcile": True,
            }
        )
        cls.accrual_invoice = (
            cls.env["account.move"]
            .with_context(default_move_type="out_invoice")
            .create(
                {
                    "company_id": cls.company.id,
                    "partner_id": cls.env.ref("base.res_partner_18").id,
                    "journal_id": cls.sale_journal.id,
                    "state": "draft",
                    "move_type": "out_invoice",
                    "invoice_date": fields.Date.today(),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Otpez Laptop without OS",
                                "price_unit": 642,
                                "quantity": 4,
                                "account_id": cls.rev_account.id,
                            },
                        )
                    ],
                }
            )
        )
        cls.company.write(
            {
                "default_accrued_revenue_account_id": cls.accrual_account.id,
                "default_accrued_expense_account_id": cls.accrual_account.id,
                "default_cutoff_journal_id": cls.accrual_journal.id,
            }
        )
        cls.payment_term = cls.env.ref("account.account_payment_term_advance_60days")

    def _create_reversals(self, move):
        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=move.ids)
            .create(
                {
                    "date": move.date,
                    "refund_method": "cancel",
                    "journal_id": move.journal_id.id,
                }
            )
        )
        return move_reversal.reverse_moves()

    def _action_accrue(self, invoice):
        accrual_wizard = (
            self.env["account.move.accrue"]
            .with_context(active_model="account.move", active_ids=[invoice.id])
            .create({})
        )
        accrual_wizard.action_accrue()

    def test_account_invoice_accrual_confirm(self):
        self.assertEqual(self.accrual_invoice.state, "draft")
        self._action_accrue(self.accrual_invoice)
        self.assertTrue(self.accrual_invoice.accrual_move_id)

        self.accrual_invoice.action_post()

        self.assertTrue(self.accrual_invoice.accrual_move_id.reversal_move_id)

        self.assertEqual(self.accrual_invoice.state, "posted")

        moves = self.env["account.move"].search(
            [("journal_id", "=", self.accrual_journal.id)]
        )
        self.assertEqual(len(moves), 2)
        move1 = moves[0]
        move2 = moves[1]
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        reverse = False
        if move1.reversal_move_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_move_id.id)
        if move2.reversal_move_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_move_id.id)
        self.assertTrue(reverse)

    def test_account_invoice_accrual_remove(self):
        self.assertEqual(self.accrual_invoice.state, "draft")
        self._action_accrue(self.accrual_invoice)
        with self.assertRaises(exceptions.Warning):
            self.accrual_invoice.unlink()
        self._create_reversals(self.accrual_invoice.accrual_move_id)
        self.accrual_invoice.unlink()

        moves = self.env["account.move"].search(
            [("journal_id", "=", self.accrual_journal.id)]
        )
        self.assertEqual(len(moves), 2)

        move1 = moves[0]
        move2 = moves[1]
        reverse = False
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        if move1.reversal_move_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_move_id.id)
        if move2.reversal_move_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_move_id.id)
        self.assertTrue(reverse)

    def test_account_invoice_reversal(self):
        self.assertEqual(self.accrual_invoice.state, "draft")
        self._action_accrue(self.accrual_invoice)

        self._create_reversals(self.accrual_invoice.accrual_move_id)

        moves = self.env["account.move"].search(
            [("journal_id", "=", self.accrual_journal.id)]
        )
        self.assertEqual(len(moves), 2)

        move1 = moves[0]
        move2 = moves[1]
        reverse = False
        self.assertFalse(move1.to_be_reversed)
        self.assertFalse(move2.to_be_reversed)
        if move1.reversal_move_id:
            reverse = True
            self.assertEqual(move2.id, move1.reversal_move_id.id)
        if move2.reversal_move_id:
            reverse = True
            self.assertEqual(move1.id, move2.reversal_move_id.id)
        self.assertTrue(reverse)

    def test_accrual_with_payment_term(self):
        """check that accrual move have line for each payment term"""
        self.accrual_invoice.invoice_payment_term_id = self.payment_term
        self._action_accrue(self.accrual_invoice)
        accrual_move = self.accrual_invoice.accrual_move_id
        self.assertSetEqual(
            set(
                accrual_move.line_ids.filtered("date_maturity").mapped("date_maturity")
            ),
            {fields.Date.today(), fields.Date.today() + timedelta(days=60)},
        )
