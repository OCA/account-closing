# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install")
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
                            "days": 15,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "balance",
                            "days_after": 15,
                            "end_month": True,
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
