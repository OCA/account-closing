# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestAccountFiscalYearClosing(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()
        cls.account_model = cls.env["account.account"]
        cls.move_line_obj = cls.env["account.move.line"]
        cls.account_type_rec = "asset_receivable"
        cls.account_type_pay = "liability_payable"
        cls.account_type_rev = "income"
        cls.account_type_exp = "expense"
        cls.account_type_ass = "asset_current"
        cls.account_type_liq = "asset_cash"
        cls.account_type_lia = "liability_current"

        cls.account_user = cls.env.user
        account_manager = cls.env["res.users"].create(
            {
                "name": "Test Account manager",
                "login": "accountmanager",
                "password": "accountmanager",
                "groups_id": [
                    (6, 0, cls.env.user.groups_id.ids),
                    (4, cls.env.ref("account.group_account_manager").id),
                ],
                "company_ids": [(6, 0, cls.account_user.company_ids.ids)],
                "company_id": cls.account_user.company_id.id,
            }
        )
        account_manager.partner_id.email = "accountmanager@test.com"

        today = fields.Date.today()
        cls.the_day = today - relativedelta(month=2, day=1)
        cls.start_of_this_year = today - relativedelta(month=1, day=1)
        cls.end_of_this_year = today + relativedelta(month=12, day=31)
        cls.start_of_next_year = today + relativedelta(years=1, month=1, day=1)

        cls.a_sale = cls.account_model.create(
            {
                "code": "reve.acc",
                "name": "revenue account",
                "account_type": cls.account_type_rev,
                "reconcile": False,
            }
        )
        cls.a_purchase = cls.account_model.create(
            {
                "code": "expe.acc",
                "name": "expense account",
                "account_type": cls.account_type_exp,
                "reconcile": False,
            }
        )
        cls.a_debit_vat = cls.account_model.create(
            {
                "code": "debvat.cc",
                "name": "debit vat account",
                "account_type": cls.account_type_ass,
                "reconcile": False,
            }
        )
        cls.a_credit_vat = cls.account_model.create(
            {
                "code": "credvat.acc",
                "name": "credit vat account",
                "account_type": cls.account_type_lia,
                "reconcile": False,
            }
        )
        cls.a_pf_closing = cls.account_model.create(
            {
                "code": "pf.acc",
                "name": "profit&loss account",
                "account_type": cls.account_type_ass,
                "reconcile": False,
            }
        )
        cls.a_bal_closing = cls.account_model.create(
            {
                "code": "bal.acc",
                "name": "financial closing account",
                "account_type": cls.account_type_lia,
                "reconcile": False,
            }
        )
        cls.payment_term_2rate = cls.env["account.payment.term"].create(
            {
                "name": "Payment term 30/60 end of month",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "delay_type": "days_after",
                            "nb_days": 15,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "delay_type": "days_after_end_of_month",
                            "nb_days": 15,
                        },
                    ),
                ],
            }
        )
        cls.closing_journal = cls.env["account.journal"].create(
            {
                "name": "Closing journal",
                "type": "general",
                "code": "CLJ",
            }
        )
        cls.purchase_tax_15 = cls.env["account.tax"].create(
            {
                "name": "Tax 15.0",
                "amount": 15.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
            }
        )
        cls.sale_tax_15 = cls.env["account.tax"].create(
            {
                "name": "Tax 15.0",
                "amount": 15.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )

    def create_simple_invoice(self, date, partner, inv_type):
        invoice = self.env["account.move"].create(
            {
                "partner_id": partner.id,
                "move_type": inv_type,
                "invoice_date": date,
                "state": "draft",
                "invoice_payment_term_id": self.payment_term_2rate.id,
                "user_id": self.account_user.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "quantity": 1.0,
                            "price_unit": 300.0 if inv_type == "out_invoice" else 100.0,
                            "name": "Invoice line",
                            "account_id": self.a_sale.id
                            if inv_type == "out_invoice"
                            else self.a_purchase.id,
                            "tax_ids": [
                                (
                                    6,
                                    0,
                                    {
                                        self.sale_tax_15.id
                                        if inv_type == "out_invoice"
                                        else self.purchase_tax_15.id
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        return invoice

    def test_account_closing(self):
        # create a supplier invoice
        supplier_invoice = self.create_simple_invoice(
            self.the_day, self.env.ref("base.res_partner_4"), "in_invoice"
        )
        self.assertTrue(
            (supplier_invoice.state == "draft"), "Supplier invoice state is not Draft"
        )
        self.assertTrue(
            (supplier_invoice.move_type == "in_invoice"),
            "Supplier invoice state is not in_invoice",
        )
        supplier_invoice.action_post()
        self.assertTrue(
            (supplier_invoice.state == "posted"), "Supplier invoice state is not Posted"
        )

        # create a customer invoice
        customer_invoice = self.create_simple_invoice(
            self.the_day, self.env.ref("base.res_partner_4"), "out_invoice"
        )
        self.assertTrue(
            (customer_invoice.state == "draft"), "Customer invoice state is not Draft"
        )
        customer_invoice.action_post()
        self.assertTrue(
            (customer_invoice.state == "posted"), "Customer invoice state is not Posted"
        )
        self.assertTrue(
            (customer_invoice.move_type == "out_invoice"),
            "Customer invoice state is not out_invoice",
        )

        move_lines = self.move_line_obj.search([])
        account_types = move_lines.mapped("account_id.account_type")
        self.assertTrue(
            (
                [
                    x
                    for x in account_types
                    if x
                    not in [
                        "asset_receivable",  # Receivable
                        "asset_current",  # Current Assets
                        "income",  # Income
                        "liability_payable",  # Payable
                        "liability_current",  # Current Liabilities
                        "expense",  # Expenses
                        "asset_cash",  # Bank and Cash
                    ]
                ]
                == []
            ),
            "There are account user types not defined!",
        )

        # Receivable
        rec_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "asset_receivable")]
        )
        # Payable
        pay_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "liability_payable")]
        )
        # Income
        inc_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "income")]
        )
        # Expenses
        exp_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "expense")]
        )
        # Current Assets
        cas_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "asset_current")]
        )
        # Current Liabilities
        cli_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "liability_current")]
        )
        # Bank and Cash
        bac_move_lines = self.move_line_obj.search(
            [("account_id.account_type", "=", "asset_cash")]
        )

        rec_accounts = rec_move_lines.mapped("account_id.code")
        pay_accounts = pay_move_lines.mapped("account_id.code")
        inc_accounts = inc_move_lines.mapped("account_id.code")
        exp_accounts = exp_move_lines.mapped("account_id.code")
        cas_accounts = cas_move_lines.mapped("account_id.code")
        cli_accounts = cli_move_lines.mapped("account_id.code")
        bac_accounts = bac_move_lines.mapped("account_id.code")

        inc_amount = sum([y.credit - y.debit for y in inc_move_lines])
        exp_amount = sum([y.debit - y.credit for y in exp_move_lines])

        fy_closing = self.env["account.fiscalyear.closing"].create(
            {
                "name": "Closing fy",
                "date_start": self.start_of_this_year,
                "date_end": self.end_of_this_year,
                "date_opening": self.start_of_next_year,
                "check_draft_moves": True,
                "move_config_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Economic Accounts Closing",
                            "journal_id": self.closing_journal.id,
                            "code": "REV",
                            "move_type": "loss_profit",
                            "closing_type_default": "balance",
                            "date": self.end_of_this_year,
                            "sequence": 1,
                            "mapping_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "src_accounts": w,
                                        "dest_account_id": [self.a_pf_closing.id],
                                    },
                                )
                                for w in inc_accounts + exp_accounts
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Profit&Loss",
                            "journal_id": self.closing_journal.id,
                            "code": "PL",
                            "move_type": "loss_profit",
                            "closing_type_default": "balance",
                            "date": self.end_of_this_year,
                            "sequence": 2,
                            "mapping_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "name": "profit & loss",
                                        "src_accounts": "pf_acc",
                                        "dest_account_id": [self.a_bal_closing.id],
                                    },
                                ),
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Financial Accounts Closing",
                            "journal_id": self.closing_journal.id,
                            "code": "FCL",
                            "move_type": "closing",
                            "closing_type_default": "unreconciled",
                            "date": self.end_of_this_year,
                            "sequence": 3,
                            "mapping_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "src_accounts": z,
                                    },
                                )
                                for z in rec_accounts
                                + pay_accounts
                                + cas_accounts
                                + cli_accounts
                                + bac_accounts
                                + ["bal_acc"]
                            ],
                        },
                    ),
                ],
            }
        )

        res = fy_closing.button_calculate()
        if res and isinstance(res, dict) and res.get("name", False):
            self.assertFalse(
                ("Unbalanced journal entry found" == res["name"]),
                "There are unbalanced move/s in the closing moves!",
            )

        closing_move_lines = self.env["account.move.line"].search(
            [("move_id.fyc_id", "in", fy_closing.ids)]
        )
        pl_move_line = closing_move_lines.filtered(
            lambda y: y.account_id == self.a_pf_closing and y.debit == 0.0
        )
        self.assertAlmostEqual(
            pl_move_line.mapped("balance")[0], exp_amount - inc_amount
        )

        result_move_line = closing_move_lines.filtered(
            lambda y: y.account_id == self.a_bal_closing
        )
        self.assertAlmostEqual(
            result_move_line.mapped("balance")[0], exp_amount - inc_amount
        )

        posted = fy_closing.button_post()
        self.assertTrue(posted, "Fiscal Year closing is not posted!")


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

    def test_split_by_partner_keeps_foreign_currency(self):
        # When the receivable account is held in a foreign currency, the
        # per-partner closing lines must carry currency_id/amount_currency
        # over, exactly like the aggregate path does.
        company_currency = self.env.company.currency_id
        other_currency = self.setup_other_currency("EUR")
        if other_currency == company_currency:
            other_currency = self.setup_other_currency("USD")
        fx_account = self.env["account.account"].create(
            {
                "code": "CLBPFX",
                "name": "FX Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
                "currency_id": other_currency.id,
            }
        )
        rev_account = self.company_data["default_account_revenue"]
        for partner in (self.partner_a, self.partner_b):
            partner.property_account_receivable_id = fx_account
            invoice = self.env["account.move"].create(
                {
                    "partner_id": partner.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.date_start + relativedelta(days=10),
                    "currency_id": other_currency.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "quantity": 1.0,
                                "price_unit": 100.0,
                                "name": "Test FX",
                                "account_id": rev_account.id,
                            },
                        )
                    ],
                }
            )
            invoice.action_post()

        fyc = self.env["account.fiscalyear.closing"].create(
            {
                "name": "Test FX Closing",
                "date_start": self.date_start,
                "date_end": self.date_end,
                "date_opening": self.date_opening,
                "check_draft_moves": False,
                "split_by_partner": True,
                "move_config_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "FX Receivable Closing",
                            "journal_id": self.closing_journal.id,
                            "code": "RECFX",
                            "move_type": "closing",
                            "closing_type_default": "balance",
                            "date": self.date_end,
                            "sequence": 1,
                            "mapping_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "src_accounts": fx_account.code,
                                        "dest_account_id": self.closing_account.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        fyc.button_calculate()
        self.assertEqual(fyc.state, "calculated")

        closing_lines = fyc.move_ids.line_ids.filtered(
            lambda line: line.account_id == fx_account
        )
        self.assertEqual(len(closing_lines), 2)
        for partner in (self.partner_a, self.partner_b):
            line = closing_lines.filtered(lambda ln, p=partner: ln.partner_id == p)
            self.assertEqual(len(line), 1)
            self.assertEqual(line.currency_id, other_currency)
            self.assertNotEqual(line.amount_currency, 0.0)
