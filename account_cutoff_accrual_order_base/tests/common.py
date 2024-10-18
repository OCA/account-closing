# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestAccountCutoffAccrualOrderCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.cutoff_journal = cls.env["account.journal"].create(
            {
                "code": "cop0",
                "company_id": cls.company.id,
                "name": "Cutoff Journal Picking",
                "type": "general",
            }
        )
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "Cutoff account",
                "code": "ACC480000",
                "company_id": cls.company.id,
                "account_type": "liability_current",
            }
        )
        cls.company.write(
            {
                "default_accrued_revenue_account_id": cls.cutoff_account.id,
                "default_accrued_expense_account_id": cls.cutoff_account.id,
                "default_cutoff_journal_id": cls.cutoff_journal.id,
            }
        )

        cls.partner = cls.env.ref("base.res_partner_1")
        cls.products = cls.env.ref("product.product_delivery_01") | cls.env.ref(
            "product.product_delivery_02"
        )
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        for p in cls.products:
            cls.env["stock.quant"]._update_available_quantity(
                p, cls.stock_location, 100
            )
        cls.products |= cls.env.ref("product.expense_product")
        # analytic account
        cls.default_plan = cls.env["account.analytic.plan"].create(
            {"name": "Default", "company_id": False}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "analytic_account",
                "plan_id": cls.default_plan.id,
                "company_id": False,
            }
        )

    def _refund_invoice(self, invoice, post=True):
        credit_note_wizard = (
            self.env["account.move.reversal"]
            .with_context(
                **{
                    "active_ids": invoice.ids,
                    "active_id": invoice.id,
                    "active_model": "account.move",
                    "tz": self.env.company.partner_id.tz or "UTC",
                }
            )
            .create(
                {
                    "refund_method": "refund",
                    "reason": "refund",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        invoice_refund = self.env["account.move"].browse(
            credit_note_wizard.reverse_moves()["res_id"]
        )
        invoice_refund.ref = invoice_refund.id
        if post:
            invoice_refund.action_post()
        return invoice_refund
