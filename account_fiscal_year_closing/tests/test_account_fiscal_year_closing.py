# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.account.tests.account_test_users import AccountTestUsers


class TestAccountFiscalYearClosing(AccountTestUsers):
    def setUp(self):
        super().setUp()
        self.move_line_obj = self.env["account.move.line"]
        self.account_type_rec = self.env.ref("account.data_account_type_receivable")
        self.account_type_pay = self.env.ref("account.data_account_type_payable")
        self.account_type_rev = self.env.ref("account.data_account_type_revenue")
        self.account_type_exp = self.env.ref("account.data_account_type_expenses")
        self.account_type_ass = self.env.ref("account.data_account_type_current_assets")
        self.account_type_liq = self.env.ref("account.data_account_type_liquidity")
        self.account_type_lia = self.env.ref(
            "account.data_account_type_current_liabilities"
        )

        today = fields.Date.today()
        self.the_day = today - relativedelta(month=2, day=1)
        self.start_of_this_year = today - relativedelta(month=1, day=1)
        self.end_of_this_year = today + relativedelta(month=12, day=31)
        self.start_of_next_year = today + relativedelta(years=1, month=1, day=1)

        self.a_rec = self.account_model.sudo(self.account_manager.id).create(
            {
                "code": "cust_acc",
                "name": "customer account",
                "user_type_id": self.account_type_rec.id,
                "reconcile": True,
            }
        )
        self.a_pay = self.account_model.sudo(self.account_manager.id).create(
            {
                "code": "supp_acc",
                "name": "supplier account",
                "user_type_id": self.account_type_pay.id,
                "reconcile": True,
            }
        )
        self.a_sale = self.account_model.create(
            {
                "code": "reve_acc",
                "name": "revenue account",
                "user_type_id": self.account_type_rev.id,
                "reconcile": False,
            }
        )
        self.a_purchase = self.account_model.create(
            {
                "code": "expe_acc",
                "name": "expense account",
                "user_type_id": self.account_type_exp.id,
                "reconcile": False,
            }
        )
        self.a_debit_vat = self.account_model.create(
            {
                "code": "debvat_acc",
                "name": "debit vat account",
                "user_type_id": self.account_type_ass.id,
                "reconcile": False,
            }
        )
        self.a_credit_vat = self.account_model.create(
            {
                "code": "credvat_acc",
                "name": "credit vat account",
                "user_type_id": self.account_type_lia.id,
                "reconcile": False,
            }
        )
        self.a_pf_closing = self.account_model.create(
            {
                "code": "pf_acc",
                "name": "profit&loss account",
                "user_type_id": self.account_type_ass.id,
                "reconcile": False,
            }
        )
        self.a_bal_closing = self.account_model.create(
            {
                "code": "bal_acc",
                "name": "financial closing account",
                "user_type_id": self.account_type_lia.id,
                "reconcile": False,
            }
        )
        self.payment_term_2rate = self.env["account.payment.term"].create(
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
        self.sale_journal = self.env["account.journal"].search([("type", "=", "sale")])[
            0
        ]
        self.purchase_journal = self.env["account.journal"].search(
            [("type", "=", "purchase")]
        )[0]
        self.closing_journal = self.env["account.journal"].create(
            {
                "name": "Closing journal",
                "type": "general",
                "code": "CLJ",
                "update_posted": True,
            }
        )
        self.purchase_tax_15 = self.env["account.tax"].create(
            {
                "name": "Tax 15.0",
                "amount": 15.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "account_id": self.a_credit_vat.id,
            }
        )
        self.sale_tax_15 = self.env["account.tax"].create(
            {
                "name": "Tax 15.0",
                "amount": 15.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "account_id": self.a_debit_vat.id,
            }
        )

    def create_simple_invoice(self, date, partner, inv_type):
        invoice = self.env["account.invoice"].create(
            {
                "partner_id": partner.id,
                "account_id": self.a_rec.id
                if inv_type == "out_invoice"
                else self.a_pay.id,
                "type": inv_type,
                "journal_id": self.sale_journal.id
                if inv_type == "out_invoice"
                else self.purchase_journal.id,
                "date_invoice": date,
                "state": "draft",
                "payment_term_id": self.payment_term_2rate.id,
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
                            "invoice_line_tax_ids": [
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

    def test_accoung_closing(self):
        # create a supplier invoice
        supplier_invoice = self.create_simple_invoice(
            self.the_day, self.env.ref("base.res_partner_4"), "in_invoice"
        )
        self.assertTrue(
            (supplier_invoice.state == "draft"), "Supplier invoice state is not Draft"
        )
        self.assertTrue(
            (supplier_invoice.type == "in_invoice"),
            "Supplier invoice state is not in_invoice",
        )
        supplier_invoice.action_invoice_open()
        self.assertTrue(
            (supplier_invoice.state == "open"), "Supplier invoice state is not Open"
        )

        # create a customer invoice
        customer_invoice = self.create_simple_invoice(
            self.the_day, self.env.ref("base.res_partner_4"), "out_invoice"
        )
        self.assertTrue(
            (customer_invoice.state == "draft"), "Customer invoice state is not Draft"
        )
        customer_invoice.action_invoice_open()
        self.assertTrue(
            (customer_invoice.state == "open"), "Customer invoice state is not Open"
        )
        self.assertTrue(
            (customer_invoice.type == "out_invoice"),
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
            pl_move_line.mapped("credit")[0], exp_amount - inc_amount
        )

        result_move_line = closing_move_lines.filtered(
            lambda y: y.account_id == self.a_bal_closing
        )
        self.assertAlmostEqual(
            result_move_line.mapped("credit")[0], exp_amount - inc_amount
        )

        posted = fy_closing.button_post()
        self.assertTrue(posted, "Fiscal Year closing is not posted!")
