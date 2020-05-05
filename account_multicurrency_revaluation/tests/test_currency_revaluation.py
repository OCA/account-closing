# Copyright 2012-2018 Camptocamp SA
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import SavepointCase


class TestCurrencyRevaluation(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        cls.company = ref("account_multicurrency_revaluation.res_company_reval")
        cls.env.user.write({"company_ids": [(4, cls.company.id, False)]})
        cls.env.user.company_id = cls.company
        cls.reval_journal = ref("account_multicurrency_revaluation.reval_journal")
        cls.company.write(
            {
                "revaluation_loss_account_id": cls.env.ref(
                    "account_multicurrency_revaluation.acc_reval_loss"
                ).id,
                "revaluation_gain_account_id": cls.env.ref(
                    "account_multicurrency_revaluation." "acc_reval_gain"
                ).id,
                "currency_reval_journal_id": cls.reval_journal.id,
            }
        )
        sales_journal = ref("account_multicurrency_revaluation.sales_journal")
        cls.receivable_acc = cls.env["account.account"].create(
            {
                "name": "Account Receivable",
                "code": "accrec",
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
                "currency_revaluation": True,
                "reconcile": True,
                "company_id": cls.company.id,
            }
        )
        payable_acc = ref("account_multicurrency_revaluation.demo_acc_payable")
        revenue_acc = ref("account_multicurrency_revaluation.demo_acc_revenue")
        # create invoice in USD
        usd_currency = ref("base.USD")
        bank_journal_usd = ref("account_multicurrency_revaluation.bank_journal_usd")
        bank_journal_usd.currency_id = usd_currency.id
        invoice_line_data = {
            "product_id": ref("product.product_product_5").id,
            "quantity": 1.0,
            "account_id": revenue_acc.id,
            "name": "product test 5",
            "price_unit": 800.00,
            "currency_id": usd_currency.id,
        }
        cls.partner = ref("base.res_partner_3")
        cls.partner.company_id = cls.company.id
        cls.partner.property_account_payable_id = payable_acc.id
        cls.partner.property_account_receivable_id = cls.receivable_acc.id

        payment_term = ref("account.account_payment_term_end_following_month")

        cls.year = year = str(fields.Date.today().year)
        # Currency rates
        dates = ("%s-01-15" % year, "%s-02-15" % year, "%s-03-15" % year)
        rates = (2, 4, 2.5)
        cls.create_rates(cls, dates, rates, usd_currency)
        # Invoice
        invoice = cls.env["account.move"].create(
            {
                "type": "out_invoice",
                "invoice_date": "%s-01-16" % year,
                "currency_id": usd_currency.id,
                "company_id": cls.company.id,
                "journal_id": sales_journal.id,
                "partner_id": cls.partner.id,
                "invoice_line_ids": [(0, 0, invoice_line_data)],
                "invoice_payment_term_id": payment_term.id,
            }
        )
        # Post entries
        invoice.post()

        payment_method = ref(
            "account_multicurrency_revaluation." "account_payment_method_manual_in"
        )

        # Register partial payment
        payment = cls.env["account.payment"].create(
            {
                "invoice_ids": [(4, invoice.id, 0)],
                "amount": 700,
                "currency_id": usd_currency.id,
                "payment_date": "%s-02-15" % year,
                "communication": "Invoice partial payment",
                "partner_id": invoice.partner_id.id,
                "partner_type": "customer",
                "journal_id": bank_journal_usd.id,
                "payment_type": "inbound",
                "payment_method_id": payment_method.id,
                "payment_difference_handling": "open",
                "writeoff_account_id": False,
            }
        )
        payment.post()

        # create invoice in GBP
        gbp_currency = ref("base.GBP")

        bank_journal_gbp = ref("account_multicurrency_revaluation.bank_journal_gbp")

        bank_journal_gbp.currency_id = gbp_currency.id

        invoice_line_data = {
            "product_id": cls.env.ref("product.product_product_5").id,
            "quantity": 1.0,
            "account_id": revenue_acc.id,
            "name": "product test 5",
            "price_unit": 800.00,
            "currency_id": gbp_currency.id,
        }

        invoice = cls.env["account.move"].create(
            {
                "type": "out_invoice",
                "invoice_date": "%s-01-16" % year,
                "currency_id": gbp_currency.id,
                "journal_id": sales_journal.id,
                "company_id": cls.company.id,
                "partner_id": ref("base.res_partner_3").id,
                "invoice_line_ids": [(0, 0, invoice_line_data)],
                "invoice_payment_term_id": payment_term.id,
            }
        )
        # Post entries
        invoice.post()

        # Register partial payment
        payment = cls.env["account.payment"].create(
            {
                "invoice_ids": [(4, invoice.id, 0)],
                "amount": 700,
                "currency_id": gbp_currency.id,
                "payment_date": "%s-02-15" % year,
                "communication": "Invoice partial payment",
                "partner_id": invoice.partner_id.id,
                "partner_type": "customer",
                "journal_id": bank_journal_gbp.id,
                "payment_type": "inbound",
                "payment_method_id": payment_method.id,
                "payment_difference_handling": "open",
                "writeoff_account_id": False,
            }
        )
        payment.post()

    def test_uk_revaluation(self):
        self.assertEqual(self.company.currency_id, self.env.ref("base.EUR"))

        wizard = self.env["wizard.currency.revaluation"]
        data = {
            "revaluation_date": "%s-03-15" % self.year,
            "journal_id": self.reval_journal.id,
            "label": "[%(account)s,%(rate)s] wiz_test",
        }
        wiz = wizard.create(data)
        result = wiz.revaluate_currency()

        # Assert the wizard show the created revaluation lines
        self.assertEqual(result.get("name"), "Created revaluation lines")

        reval_move_lines = self.env["account.move.line"].search(
            [("name", "like", "wiz_test")]
        )

        # Assert 8 account.move.line were generated
        self.assertEqual(len(reval_move_lines), 8)

        for reval_line in reval_move_lines:

            label = reval_line.name
            rate = label[label.find(",") + 1 : label.find("]")].strip()
            self.assertEqual(rate, "2.5")

            if reval_line.account_id.name == "Account Liquidity USD":
                self.assertFalse(reval_line.partner_id)
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 105.0)
            elif reval_line.account_id.name == "Account Liquidity GBP":
                self.assertFalse(reval_line.partner_id)
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 105.0)
            elif reval_line.account_id.name == "Account Receivable":
                self.assertIsNotNone(reval_line.partner_id.id)
                self.assertEqual(reval_line.credit, 185.0)
                self.assertEqual(reval_line.debit, 0.0)
            elif reval_line.account_id.name == "Reval Gain":
                self.assertEqual(reval_line.credit, 105.0)
                self.assertEqual(reval_line.debit, 0.0)
            elif reval_line.account_id.name == "Reval Loss":
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 185.0)

    def _test_defaults(self):
        # TODO: This causes that the environment to be reset and screw up tests,
        # so disabled for now
        self.env["res.config.settings"].create(
            {
                "default_currency_reval_journal_id": self.reval_journal.id,
                "revaluation_loss_account_id": self.env.ref(
                    "account_multicurrency_revaluation." "acc_reval_loss"
                ).id,
                "revaluation_gain_account_id": self.env.ref(
                    "account_multicurrency_revaluation." "acc_reval_gain"
                ).id,
            }
        ).execute()

        wizard = self.env["wizard.currency.revaluation"].create(
            {"journal_id": self.reval_journal.id}
        )

        self.assertEqual(wizard.revaluation_date, fields.date.today())
        self.assertEqual(wizard.journal_id, self.reval_journal)

    def test_us_revaluation(self):
        """Create Invoices and Run the revaluation currency wizard
        with different rates which result should be:
                                 Debit    Credit    Amount Currency
        Customer Invoice US      25.00    0.00      100.00
        Customer Invoice US      40.00    0.00      100.00

        Fisrt wizard execution:

            Currency Reval. 1.0  135.00   0.00    0.00

        Second wizard execution:

            Currency Reval 1.25    0.00   40.00     0.00
        """
        self.delete_journal_data()
        usd_currency = self.env.ref("base.USD")
        dates = (
            fields.Date.today() - timedelta(days=30),
            fields.Date.today() - timedelta(days=15),
            fields.Date.today() - timedelta(days=7),
            fields.Date.today() - timedelta(days=1),
        )
        rates = (4.00, 2.50, 1.00, 1.25)
        self.create_rates(dates, rates, usd_currency)
        invoice1 = self.create_invoice(
            fields.Date.today() - timedelta(days=30), usd_currency, 1.0, 100.00
        )
        invoice1.post()
        invoice2 = self.create_invoice(
            fields.Date.today() - timedelta(days=15), usd_currency, 1.0, 100.00
        )
        invoice2.post()
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertEqual(sum(reval_move_lines.mapped("debit")), 65.00)
        self.assertEqual(sum(reval_move_lines.mapped("amount_currency")), 200.00)

        result = self.wizard_execute(fields.Date.today() - timedelta(days=7))
        self.assertEqual(result.get("name"), "Created revaluation lines")
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertEqual(sum(reval_move_lines.mapped("debit")), 200.00)
        self.assertEqual(sum(reval_move_lines.mapped("amount_currency")), 200.00)

        result = self.wizard_execute(fields.Date.today() - timedelta(days=1))
        self.assertEqual(result.get("name"), "Created revaluation lines")
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertEqual(sum(reval_move_lines.mapped("debit")), 200.00)
        self.assertEqual(sum(reval_move_lines.mapped("credit")), 40.00)
        self.assertEqual(sum(reval_move_lines.mapped("amount_currency")), 200.00)

        wizard = self.env["unrealized.report.printer"]
        wiz = wizard.create({})
        result = wiz.print_report()
        account_ids = result.get("context").get("active_ids")
        report = (
            self.env["account.move.line"]
            .search([("account_id", "in", account_ids)])
            .filtered(lambda l: l.account_id.code == "accrec")
        )
        self.assertEqual(sum(report.mapped("debit")), 200)
        self.assertEqual(sum(report.mapped("credit")), 40)
        self.assertEqual(sum(report.mapped("amount_currency")), 200)

    def test_revaluation_payment(self):
        """Create an Invoice and execute the revaluation currency wizard with
        a rate of 0.75:
                                    Debit    Credit       Amount Currency
        Account Receivable
          currency revaluation      0.00     2666.67      0.00
          customer invoices         6666.67  0.00         5000.00

        Make a payment with 1.0 rate and execute the revaluation currency
        wizard with a rate of 1.25:

                                    Debit     Credit      Amount Currency
        Account Receivable
          currency revaluation      0.00      2666.67     0.00
          currency revaluation      0.00      800.00      0.00
          euro bank                 0.00      4000.00    -4000.00
          customer invoices         6666.67   0.00        5000.00

        """
        self.delete_journal_data()
        usd_currency = self.env.ref("base.USD")
        eur_currency = self.env.ref("base.EUR")
        self.company.currency_id = usd_currency.id
        dates = (
            fields.Date.to_date("%s-11-10" % self.year),
            fields.Date.to_date("%s-11-14" % self.year),
            fields.Date.to_date("%s-11-16" % self.year),
        )
        rates = (0.75, 1.00, 1.25)
        self.create_rates(dates, rates, eur_currency)
        self.create_rates([fields.Date.to_date("2001-01-01")], [1], usd_currency)
        invoice = self.create_invoice(
            fields.Date.to_date("%s-11-11" % self.year), eur_currency, 5.0, 1000.00
        )
        invoice.post()
        result = self.wizard_execute(fields.Date.to_date("%s-11-16" % self.year))
        self.assertEqual(result.get("name"), "Created revaluation lines")
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertAlmostEqual(sum(reval_move_lines.mapped("debit")), 6666.67)
        self.assertAlmostEqual(sum(reval_move_lines.mapped("credit")), 2666.67)
        self.assertAlmostEqual(sum(reval_move_lines.mapped("amount_currency")), 5000.00)

        euro_bank = self.env["account.journal"].create(
            {
                "name": "Euro Bank",
                "type": "bank",
                "code": "EURBK",
                "currency_id": eur_currency.id,
            }
        )
        euro_bank.default_debit_account_id.currency_revaluation = True
        payment_method = self.env.ref(
            "account_multicurrency_revaluation." "account_payment_method_manual_in"
        )

        # Register partial payment
        payment = self.env["account.payment"].create(
            {
                "invoice_ids": [(4, invoice.id, 0)],
                "amount": 4000,
                "currency_id": eur_currency.id,
                "payment_date": "%s-11-15" % self.year,
                "communication": "Invoice partial payment",
                "partner_id": invoice.partner_id.id,
                "partner_type": "customer",
                "journal_id": euro_bank.id,
                "payment_type": "inbound",
                "payment_method_id": payment_method.id,
                "payment_difference_handling": "open",
                "writeoff_account_id": False,
            }
        )
        payment.post()

        result = self.wizard_execute(fields.Date.to_date("%s-11-16" % self.year))
        self.assertEqual(result.get("name"), "Created revaluation lines")
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertEqual(sum(reval_move_lines.mapped("debit")), 7466.67)
        self.assertEqual(sum(reval_move_lines.mapped("credit")), 6666.67)
        self.assertEqual(sum(reval_move_lines.mapped("amount_currency")), 1000.00)

        receivable_lines = len(reval_move_lines)
        result = self.wizard_execute(fields.Date.to_date("%s-11-16" % self.year))
        reval_move_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.receivable_acc.id)]
        )
        self.assertEqual(len(reval_move_lines), receivable_lines)

    def create_rates(self, dates, rates, currency):
        currency.rate_ids.unlink()
        for date, rate in zip(dates, rates):
            self.env["res.currency.rate"].create(
                {
                    "currency_id": currency.id,
                    "company_id": self.company.id,
                    "name": date,
                    "rate": rate,
                }
            )

    def create_invoice(self, date, currency, quantity, price):
        revenue_acc = self.env.ref("account_multicurrency_revaluation.demo_acc_revenue")
        payment_term = self.env.ref("account.account_payment_term_end_following_month")
        sales_journal = self.env.ref("account_multicurrency_revaluation.sales_journal")
        invoice_line_data = {
            "product_id": self.env.ref("product.product_product_5").id,
            "quantity": quantity,
            "account_id": revenue_acc.id,
            "name": "product test 5",
            "price_unit": price,
            "currency_id": currency.id,
        }
        invoice = self.env["account.move"].create(
            {
                "type": "out_invoice",
                "invoice_date": date,
                "currency_id": currency.id,
                "journal_id": sales_journal.id,
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "invoice_line_ids": [(0, 0, invoice_line_data)],
                "invoice_payment_term_id": payment_term.id,
            }
        )
        return invoice

    def wizard_execute(self, date):
        data = {
            "revaluation_date": date,
            "journal_id": self.reval_journal.id,
            "label": "[%(account)s] [%(currency)s] wiz_test",
        }
        wiz = self.env["wizard.currency.revaluation"].create(data)
        return wiz.revaluate_currency()

    def delete_journal_data(self):
        """Delete journal data
        delete all journal-related data, so a new currency can be set.
        """

        company = self.company
        invoices = self.env["account.move"].search([("company_id", "=", company.id)])
        invoices.button_draft()

        models_to_clear = [
            "account.move.line",
            "account.move",
            "account.bank.statement",
        ]
        for model in models_to_clear:
            records = (
                self.env[model]
                .with_context(force_delete=True)
                .search([("company_id", "=", company.id)])
            )
            if model == "account.move.line":
                records.remove_move_reconcile()
            records.unlink()
