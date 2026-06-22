from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestFiscalYearClosingByPartner(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = fields.Date.today()
        cls.date_start = today.replace(month=1, day=1)
        cls.date_end = today.replace(month=12, day=31)
        cls.date_opening = cls.date_end + relativedelta(days=1)

        cls.closing_journal = cls.env["account.journal"].create(
            {"name": "Closing Journal", "type": "general", "code": "CLBP"}
        )
        cls.rec_account = cls.company_data["default_account_receivable"]
        cls.closing_account = cls.env["account.account"].create(
            {
                "code": "CLBPACC",
                "name": "FYC Balance Closing Account",
                "account_type": "equity",
                "reconcile": False,
            }
        )
        rev_account = cls.company_data["default_account_revenue"]

        # partner_b uses a copy of the default receivable account by default in
        # AccountTestInvoicingCommon; override it so both partners post their
        # receivable lines on the same rec_account used in the FYC mapping.
        cls.partner_b.property_account_receivable_id = cls.rec_account

        for partner in (cls.partner_a, cls.partner_b):
            invoice = cls.env["account.move"].create(
                {
                    "partner_id": partner.id,
                    "move_type": "out_invoice",
                    "invoice_date": cls.date_start + relativedelta(days=10),
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "quantity": 1.0,
                                "price_unit": 100.0,
                                "name": "Test",
                                "account_id": rev_account.id,
                            },
                        )
                    ],
                }
            )
            invoice.action_post()

    def _create_fyc(self, split_by_partner):
        return self.env["account.fiscalyear.closing"].create(
            {
                "name": "Test Closing",
                "date_start": self.date_start,
                "date_end": self.date_end,
                "date_opening": self.date_opening,
                "check_draft_moves": False,
                "split_by_partner": split_by_partner,
                "move_config_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Receivable Closing",
                            "journal_id": self.closing_journal.id,
                            "code": "REC",
                            "move_type": "closing",
                            "closing_type_default": "balance",
                            "date": self.date_end,
                            "sequence": 1,
                            "mapping_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "src_accounts": self.rec_account.code,
                                        "dest_account_id": self.closing_account.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )

    def test_split_by_partner_creates_per_partner_lines(self):
        fyc = self._create_fyc(split_by_partner=True)
        fyc.button_calculate()
        self.assertEqual(fyc.state, "calculated")

        closing_lines = fyc.move_ids.line_ids.filtered(
            lambda line: line.account_id == self.rec_account
        )
        partners_on_lines = closing_lines.mapped("partner_id")
        self.assertIn(self.partner_a, partners_on_lines)
        self.assertIn(self.partner_b, partners_on_lines)

    def test_no_split_aggregates_lines(self):
        fyc = self._create_fyc(split_by_partner=False)
        fyc.button_calculate()
        self.assertEqual(fyc.state, "calculated")

        closing_lines = fyc.move_ids.line_ids.filtered(
            lambda line: line.account_id == self.rec_account
        )
        self.assertEqual(len(closing_lines), 1)
        self.assertFalse(closing_lines.partner_id)
