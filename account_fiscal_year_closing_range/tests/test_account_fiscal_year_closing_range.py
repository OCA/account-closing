# Copyright 2025 Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountFiscalYearClosingRange(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.FiscalClosing = cls.env["account.fiscalyear.closing"]
        cls.Config = cls.env["account.fiscalyear.closing.config"]
        cls.Mapping = cls.env["account.fiscalyear.closing.mapping"]
        cls.Wizard = cls.env["fiscalyear.closing.range.wizard"]
        cls.Account = cls.env["account.account"]
        cls.Move = cls.env["account.move"]
        cls.Journal = cls.env["account.journal"]

        cls.user_type = cls.env.ref(
            "account.data_account_type_current_assets", raise_if_not_found=False
        )

        def get_or_create_account(code, name):
            account = cls.Account.search(
                [("code", "=", code), ("company_ids", "in", [cls.env.company.id])],
                limit=1,
            )
            if not account:
                vals = {
                    "code": code,
                    "name": name,
                    "account_type": "asset_current",
                    "company_ids": [(6, 0, [cls.env.company.id])],
                }

                if cls.user_type:
                    vals["user_type_id"] = cls.user_type.id

                account = cls.Account.create(vals)
            return account

        cls.acc_1 = get_or_create_account("100100", "Account 100100")
        cls.acc_2 = get_or_create_account("100200", "Account 100200")
        cls.acc_3 = get_or_create_account("100300", "Account 100300")
        cls.acc_out = get_or_create_account("100400", "Account Out of Range")
        cls.acc_dest = get_or_create_account("999999", "Destination Account")

        cls.journal = cls.Journal.search(
            [("type", "=", "general"), ("company_id", "=", cls.env.company.id)], limit=1
        )

    def _create_balance(self, account, amount):
        move = self.Move.create(
            {
                "journal_id": self.journal.id,
                "date": "2025-06-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "debit": amount,
                            "name": "Test Debit",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.acc_dest.id,
                            "credit": amount,
                            "name": "Offset Credit",
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _create_fiscal_closing_form(self, year, date_start, date_end, date_opening):
        with Form(self.env["account.fiscalyear.closing"]) as fyc_form:
            fyc_form.year = year
            fyc_form.date_start = date_start
            fyc_form.date_end = date_end
            fyc_form.date_opening = date_opening
        return fyc_form.save()

    def _create_config_with_context(self, fyc_id, journal_id):
        return self.Config.with_context(fyc_id=fyc_id.id).create(
            {
                "fyc_id": fyc_id.id,
                "journal_id": journal_id.id,
                "closing_type_default": "balance",
                "name": fyc_id.name,
                "code": "CLOSE",
                "enabled": True,
                "move_type": "closing",
                "date": fyc_id.date_end,
            }
        )

    def _create_mapping_with_context(
        self, fyc_config_id, code_start, code_end, dest_account
    ):
        return self.Mapping.with_context(fyc_config_id=fyc_config_id.id).create(
            {
                "fyc_config_id": fyc_config_id.id,
                "code_start": code_start,
                "code_end": code_end,
                "src_accounts": code_start or "RANGE",
                "dest_account_id": [dest_account.id],
            }
        )

    def test_01_create_fiscal_closing_using_form(self):
        fyc = self._create_fiscal_closing_form(
            year=2025,
            date_start="2025-01-01",
            date_end="2025-12-31",
            date_opening="2026-01-01",
        )
        self.assertTrue(fyc.id)
        self.assertIn("2025", fyc.name)
        fyc.unlink()

    def test_02_create_config_with_mapping_range(self):
        fyc = self._create_fiscal_closing_form(
            year=2025,
            date_start="2025-01-01",
            date_end="2025-12-31",
            date_opening="2026-01-01",
        )
        config = self._create_config_with_context(fyc_id=fyc, journal_id=self.journal)
        mapping = self._create_mapping_with_context(
            fyc_config_id=config,
            code_start="100100",
            code_end="100300",
            dest_account=self.acc_dest,
        )
        self.assertTrue(mapping.id)
        domain = config._get_mapping_account_domain(mapping)
        self.assertEqual(
            domain,
            [
                ("company_ids", "in", [self.env.company.id]),
                ("code", ">=", "100100"),
                ("code", "<=", "100300"),
            ],
        )
        fyc.unlink()

    def test_03_wizard_preview_accounts(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "100100"
            wizard_form.code_end = "100300"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard = wizard_form.save()
        preview_codes = wizard.preview_account_ids.mapped("code")
        self.assertIn("100100", preview_codes)
        self.assertIn("100300", preview_codes)
        self.assertEqual(len(wizard.preview_account_ids), 3)
        fyc.unlink()

    def test_04_wizard_onchange_updates_preview(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "100100"
            wizard_form.code_end = "100200"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard = wizard_form.save()
        self.assertEqual(len(wizard.preview_account_ids), 2)

        wizard.code_end = "100300"
        wizard._onchange_code_range()
        self.assertEqual(len(wizard.preview_account_ids), 3)
        fyc.unlink()

    def test_05_calculate_closing_with_range_mapping(self):
        self._create_balance(self.acc_1, 100.0)
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        self._create_mapping_with_context(config, "100100", "100300", self.acc_dest)
        fyc.calculate()
        self.assertTrue(config.move_id)
        fyc.unlink()

    def test_06_domain_calculation_empty_range(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        mapping_empty = self._create_mapping_with_context(config, "", "", self.acc_dest)
        domain = config._get_mapping_account_domain(mapping_empty)

        self.assertIn(("code", "=ilike", "RANGE"), domain)
        fyc.unlink()

    def test_07_wizard_empty_range(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "888888"
            wizard_form.code_end = "888888"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard = wizard_form.save()
        self.assertEqual(len(wizard.preview_account_ids), 0)
        fyc.unlink()

    def test_08_multiple_mappings_different_ranges(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        self._create_mapping_with_context(config, "100100", "100200", self.acc_dest)
        self._create_mapping_with_context(config, "100300", "100300", self.acc_dest)
        mappings = self.Mapping.search([("fyc_config_id", "=", config.id)])
        self.assertEqual(len(mappings), 2)
        fyc.unlink()

    def test_09_wizard_name_prefix(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "100100"
            wizard_form.code_end = "100100"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard_form.name_prefix = "Custom Prefix"
            wizard = wizard_form.save()
        mapping_name = wizard._prepare_mapping_vals(self.acc_1)["name"]
        self.assertIn("Custom Prefix", mapping_name)
        fyc.unlink()

    def test_10_wizard_cancel_action(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "100100"
            wizard_form.code_end = "100300"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard = wizard_form.save()
        self.assertEqual(wizard.action_cancel()["type"], "ir.actions.act_window_close")
        fyc.unlink()

    def test_11_config_move_line_generation_with_range(self):
        self._create_balance(self.acc_1, 150.0)
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        self._create_mapping_with_context(config, "100100", "100200", self.acc_dest)
        fyc.calculate()
        self.assertTrue(config.move_id)
        fyc.unlink()

    def test_12_wizard_company_filter(self):
        fyc = self._create_fiscal_closing_form(
            2025, "2025-01-01", "2025-12-31", "2026-01-01"
        )
        config = self._create_config_with_context(fyc, self.journal)
        with Form(
            self.Wizard.with_context(
                active_id=config.id, default_fyc_config_id=config.id
            )
        ) as wizard_form:
            wizard_form.code_start = "100100"
            wizard_form.code_end = "100400"
            wizard_form.dest_account_code = self.acc_dest.code
            wizard = wizard_form.save()
        self.assertEqual(wizard.company_id.id, self.env.company.id)
        fyc.unlink()
