# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAccountFiscalYearClosing(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()
        cls.account_model = cls.env["account.account"]
        cls.move_line_obj = cls.env["account.move.line"]
        cls.account_type_rec = cls.env.ref("account.data_account_type_receivable")
        cls.account_type_pay = cls.env.ref("account.data_account_type_payable")
        cls.account_type_rev = cls.env.ref("account.data_account_type_revenue")
        cls.account_type_exp = cls.env.ref("account.data_account_type_expenses")
        cls.account_type_ass = cls.env.ref("account.data_account_type_current_assets")
        cls.account_type_liq = cls.env.ref("account.data_account_type_liquidity")
        cls.account_type_lia = cls.env.ref(
            "account.data_account_type_current_liabilities"
        )

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
                "code": "reve_acc",
                "name": "revenue account",
                "user_type_id": cls.account_type_rev.id,
                "reconcile": False,
            }
        )
        cls.a_purchase = cls.account_model.create(
            {
                "code": "expe_acc",
                "name": "expense account",
                "user_type_id": cls.account_type_exp.id,
                "reconcile": False,
            }
        )
        cls.a_debit_vat = cls.account_model.create(
            {
                "code": "debvat_acc",
                "name": "debit vat account",
                "user_type_id": cls.account_type_ass.id,
                "reconcile": False,
            }
        )
        cls.a_credit_vat = cls.account_model.create(
            {
                "code": "credvat_acc",
                "name": "credit vat account",
                "user_type_id": cls.account_type_lia.id,
                "reconcile": False,
            }
        )
        cls.a_pf_closing = cls.account_model.create(
            {
                "code": "pf_acc",
                "name": "profit&loss account",
                "user_type_id": cls.account_type_ass.id,
                "reconcile": False,
            }
        )
        cls.a_bal_closing = cls.account_model.create(
            {
                "code": "bal_acc",
                "name": "financial closing account",
                "user_type_id": cls.account_type_lia.id,
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
                            "days": 15,
                            "option": "after_invoice_month",
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
        user_type_names = move_lines.mapped("account_id.user_type_id.name")
        self.assertTrue(
            (
                [
                    x
                    for x in user_type_names
                    if x
                    not in [
                        "Receivable",
                        "Current Assets",
                        "Income",
                        "Payable",
                        "Current Liabilities",
                        "Expenses",
                        "Bank and Cash",
                    ]
                ]
                == []
            ),
            "There are account user types not defined!",
        )

        rec_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Receivable")]
        )
        pay_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Payable")]
        )
        inc_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Income")]
        )
        exp_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Expenses")]
        )
        cas_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Current Assets")]
        )
        cli_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Current Liabilities")]
        )
        bac_move_lines = self.move_line_obj.search(
            [("account_id.user_type_id.name", "=", "Bank and Cash")]
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
                                        "dest_account_id": self.a_pf_closing.id,
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
                                        "dest_account_id": self.a_bal_closing.id,
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
