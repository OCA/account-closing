# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged("post_install", "-at_install")
class TestFiscalYearClosingFlow(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.journal = cls.company_data["default_journal_misc"]
        cls.receivable = cls.company_data["default_account_receivable"]
        cls.revenue = cls.company_data["default_account_revenue"]
        cls.result_account = cls.env["account.account"].create(
            {"code": "PLRES", "name": "Result", "account_type": "equity"}
        )
        cls.closing_account = cls.env["account.account"].create(
            {"code": "BALCL", "name": "Balance closing", "account_type": "equity"}
        )
        today = fields.Date.today()
        cls.year = today.year
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": today.replace(month=3, day=1),
                "journal_id": cls.journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": cls.receivable.id,
                            "debit": 100,
                            "partner_id": cls.partner_a.id,
                        }
                    ),
                    Command.create({"account_id": cls.revenue.id, "credit": 100}),
                ],
            }
        )
        move.action_post()
        cls.template = cls.env["account.fiscalyear.closing.template"].create(
            {
                "name": "Template",
                "chart_template": cls.company.chart_template,
                "move_config_ids": [
                    Command.create(
                        {
                            "name": "Profit and loss",
                            "code": "PL",
                            "sequence": 1,
                            "move_type": "loss_profit",
                            "closing_type_default": "balance",
                            "mapping_ids": [
                                Command.create(
                                    {
                                        "src_accounts": cls.revenue.code,
                                        "dest_account": cls.result_account.code,
                                    }
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "Closing",
                            "code": "CLOSE",
                            "sequence": 2,
                            "move_type": "closing",
                            "closing_type_default": "unreconciled",
                            "mapping_ids": [
                                Command.create(
                                    {
                                        "src_accounts": cls.receivable.code,
                                        "dest_account": cls.closing_account.code,
                                    }
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "Opening",
                            "code": "OPEN",
                            "sequence": 3,
                            "move_type": "opening",
                            "inverse": "CLOSE",
                            "move_date": "first_opening",
                        }
                    ),
                ],
            }
        )

    def _closing_from_template(self):
        form = Form(self.env["account.fiscalyear.closing"])
        form.year = self.year
        form.closing_template_id = self.template
        return form.save()

    def test_closing_from_template(self):
        closing = self._closing_from_template()
        self.assertEqual(closing.state, "draft")
        self.assertEqual(
            closing.move_config_ids.mapped("code"), ["PL", "CLOSE", "OPEN"]
        )
        self.assertEqual(
            closing.move_config_ids.filtered(lambda c: c.code == "OPEN").date,
            closing.date_opening,
        )

    def test_calculate_post_and_open_moves(self):
        closing = self._closing_from_template()
        self.assertIs(closing.button_calculate(), True)
        self.assertEqual(closing.state, "calculated")
        moves = self.env["account.move"].search([("fyc_id", "=", closing.id)])
        self.assertEqual(len(moves), 3)
        profit_loss = closing.move_config_ids.filtered(lambda c: c.code == "PL").move_id
        self.assertRecordValues(
            profit_loss.line_ids.sorted("balance"),
            [
                {"account_id": self.revenue.id, "balance": 100.0},
                {"account_id": self.result_account.id, "balance": -100.0},
            ][::-1],
        )
        closing.button_post()
        self.assertEqual(closing.state, "posted")
        self.assertEqual(moves.mapped("state"), ["posted"] * 3)
        for action in (closing.button_open_moves(), closing.button_open_move_lines()):
            self.env[action["res_model"]].search_count(action["domain"])
        with self.assertRaises(UserError):
            closing.unlink()

    def test_recalculate_cancel_recover_and_unlink(self):
        closing = self._closing_from_template()
        closing.button_calculate()
        first_moves = self.env["account.move"].search([("fyc_id", "=", closing.id)])
        closing.button_recalculate()
        self.assertEqual(closing.state, "calculated")
        self.assertFalse(first_moves.exists())
        self.assertEqual(
            len(self.env["account.move"].search([("fyc_id", "=", closing.id)])), 3
        )
        closing.button_cancel()
        self.assertEqual(closing.state, "cancelled")
        self.assertFalse(self.env["account.move"].search([("fyc_id", "=", closing.id)]))
        closing.button_recover()
        self.assertEqual(closing.state, "draft")
        self.assertFalse(closing.calculation_date)
        closing.unlink()
        self.assertFalse(closing.exists())

    def test_closing_tour(self):
        self.template.name = "Closing template"
        self.env.flush_all()
        self.start_tour(
            "/odoo/action-account_fiscal_year_closing.action_account_fiscalyear_closing",
            "account_fiscal_year_closing_flow",
            login=self.env.user.login,
        )

    def test_unbalanced_move_tour(self):
        self.template.name = "Closing template"
        self.template.move_config_ids.filtered(
            lambda c: c.code == "CLOSE"
        ).mapping_ids.dest_account = False
        self.env.flush_all()
        self.start_tour(
            "/odoo/action-account_fiscal_year_closing.action_account_fiscalyear_closing",
            "account_fiscal_year_closing_unbalanced",
            login=self.env.user.login,
        )

    def test_template_tour(self):
        self.start_tour(
            "/odoo/action-account_fiscal_year_closing.action_account_fiscalyear_closing_template",
            "account_fiscal_year_closing_template",
            login=self.env.user.login,
        )

    def test_unbalanced_move_wizard(self):
        """A closing without destination account cannot balance its move."""
        self.template.move_config_ids.filtered(
            lambda c: c.code == "CLOSE"
        ).mapping_ids.dest_account = False
        closing = self._closing_from_template()
        action = closing.button_calculate()
        self.assertEqual(
            action["res_model"], "account.fiscalyear.closing.unbalanced.move"
        )
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(wizard.line_ids.mapped("account_id"), self.receivable)
        self.assertEqual(closing.state, "draft")
        self.assertFalse(self.env["account.move"].search([("fyc_id", "=", closing.id)]))

    def test_draft_moves_check(self):
        draft = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today().replace(month=4, day=1),
                "journal_id": self.journal.id,
                "line_ids": [
                    Command.create({"account_id": self.receivable.id, "debit": 5}),
                    Command.create({"account_id": self.revenue.id, "credit": 5}),
                ],
            }
        )
        closing = self._closing_from_template()
        with self.assertRaises(UserError):
            closing.button_calculate()
        draft.unlink()
        closing.button_calculate()
        self.assertEqual(closing.state, "calculated")
