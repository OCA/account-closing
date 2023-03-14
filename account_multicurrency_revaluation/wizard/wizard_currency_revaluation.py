# Copyright 2012-2018 Camptocamp SA
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models
from odoo.tools import float_repr


class WizardCurrencyRevaluation(models.TransientModel):
    _name = "wizard.currency.revaluation"
    _description = "Currency Revaluation Wizard"

    @api.model
    def _get_default_revaluation_date(self):
        return fields.Date.today()

    @api.model
    def _get_default_start_revaluation_date(self):
        """
        The default date will be the first date of the month as the most typical case
        will be calculating for the lines within a month.
        """
        return fields.Date.today().replace(day=1)

    @api.model
    def _get_default_journal_id(self):
        return self.env.company.currency_reval_journal_id

    @api.model
    def _get_default_label(self):
        return "%(currency)s %(account)s %(rate)s currency revaluation"

    @api.model
    @api.depends("journal_id")
    def _get_default_revaluation_account_ids(self):
        company = self.journal_id.company_id or self.env.company
        return self.env["account.account"].search(
            [
                ("user_type_id.include_initial_balance", "=", True),
                ("currency_revaluation", "=", True),
                ("company_id", "=", company.id),
            ]
        )

    revaluation_date = fields.Date(
        required=True,
        default=lambda self: self._get_default_revaluation_date(),
    )
    start_date = fields.Date(
        string="Start Revaluation Period",
        default=lambda self: self._get_default_start_revaluation_date(),
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain=[("type", "=", "general")],
        help="You can set the default journal in company settings.",
        required=True,
        default=lambda self: self._get_default_journal_id(),
    )
    label = fields.Char(
        string="Entry description",
        size=100,
        help="This label will be inserted in entries description."
        "You can use %(account)s, %(account_name)s, %(currency)s and "
        "%(rate)s keywords.",
        required=True,
        default=lambda self: self._get_default_label(),
    )
    revaluation_account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Revaluation Accounts",
        help="Accounts that will be revaluated.",
        required=True,
        default=lambda self: self._get_default_revaluation_account_ids(),
        domain=lambda self: [("company_id", "=", self.env.company.id)],
    )

    def _create_move_and_lines(
        self,
        amount,
        debit_account_id,
        credit_account_id,
        sums,
        label,
        form,
        partner_id,
        currency_id,
        analytic_debit_acc_id=False,
        analytic_credit_acc_id=False,
        debit=False,
    ):

        base_move = {
            "journal_id": form.journal_id.id,
            "date": form.revaluation_date,
            "revaluation_to_reverse": True,
        }

        base_line = {
            "name": label,
            "partner_id": partner_id,
            "currency_id": currency_id,
            "amount_currency": 0.0,
            "date": form.revaluation_date,
        }

        base_line["gl_foreign_balance"] = sums.get("foreign_balance", 0.0)
        base_line["gl_balance"] = sums.get("balance", 0.0)
        base_line["gl_revaluated_balance"] = sums.get("revaluated_balance", 0.0)
        base_line["gl_currency_rate"] = sums.get("currency_rate", 0.0)
        revaluation_origin_line_ids = sums.get("origin_aml_id", False)

        debit_line = base_line.copy()
        credit_line = base_line.copy()

        if debit:
            debit_line.update(
                {"revaluation_origin_line_ids": [(6, 0, revaluation_origin_line_ids)]}
            )
        else:
            credit_line.update(
                {"revaluation_origin_line_ids": [(6, 0, revaluation_origin_line_ids)]}
            )

        debit_line.update(
            {"debit": amount, "credit": 0.0, "account_id": debit_account_id}
        )

        if analytic_debit_acc_id:
            debit_line.update({"analytic_account_id": analytic_debit_acc_id})

        credit_line.update(
            {"debit": 0.0, "credit": amount, "account_id": credit_account_id}
        )

        if analytic_credit_acc_id:
            credit_line.update({"analytic_account_id": analytic_credit_acc_id})

        base_move["line_ids"] = [(0, 0, debit_line), (0, 0, credit_line)]
        created_move = self.env["account.move"].create(base_move)
        if self.journal_id.company_id.auto_post_entries:
            created_move.action_post()
        return [x.id for x in created_move.line_ids]

    def _compute_unrealized_currency_gl(self, currency, balances):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation

        @param int currency: currency to revaluate
        @param dict balances: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        balance = balances.get("balance", 0.0)
        if currency == self.journal_id.company_id.currency_id:
            return {
                "currency_rate": 1.0,
                "unrealized_gain_loss": 0.0,
                "revaluated_balance": balance,
            }

        foreign_balance = balances.get("foreign_balance", 0.0)

        adjusted_balance = currency._convert(
            foreign_balance,
            self.journal_id.company_id.currency_id,
            self.journal_id.company_id,
            self.revaluation_date,
        )
        unrealized_gain_loss = adjusted_balance - balance

        return {
            "currency_rate": currency.rate,
            "unrealized_gain_loss": unrealized_gain_loss,
            "revaluated_balance": adjusted_balance,
        }

    @api.model
    def _format_balance_adjustment_label(self, fmt, account, currency, rate):
        return fmt % {
            "account": account.code or _("N/A"),
            "account_name": account.name or _("N/A"),
            "currency": currency.name or _("N/A"),
            "rate": float_repr(rate, 6),
        }

    def _write_adjust_balance(
        self, account, currency, partner_id, amount, label, form, sums
    ):
        if partner_id is None:
            partner_id = False
        company = form.journal_id.company_id or self.env.company
        created_ids = []

        amount_vs_zero = currency.compare_amounts(amount, 0.0)
        if amount_vs_zero == 1:
            if company.revaluation_gain_account_id:
                line_ids = self._create_move_and_lines(
                    amount,
                    account.id,
                    company.revaluation_gain_account_id.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency.id,
                    analytic_credit_acc_id=(company.revaluation_analytic_account_id.id),
                    debit=True,
                )
                created_ids.extend(line_ids)

            if (
                company.provision_bs_gain_account_id
                and company.provision_pl_gain_account_id
            ):
                line_ids = self._create_move_and_lines(
                    amount,
                    company.provision_bs_gain_account_id.id,
                    company.provision_pl_gain_account_id.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency.id,
                    analytic_credit_acc_id=(
                        company.provision_pl_analytic_account_id.id
                    ),
                    debit=True,
                )
                created_ids.extend(line_ids)
        elif amount_vs_zero == -1:
            if company.revaluation_loss_account_id:
                line_ids = self._create_move_and_lines(
                    -amount,
                    company.revaluation_loss_account_id.id,
                    account.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency.id,
                    analytic_debit_acc_id=(company.revaluation_analytic_account_id.id),
                )
                created_ids.extend(line_ids)

            if (
                company.provision_bs_loss_account_id
                and company.provision_pl_loss_account_id
            ):
                line_ids = self._create_move_and_lines(
                    -amount,
                    company.provision_pl_loss_account_id.id,
                    company.provision_bs_loss_account_id.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency.id,
                    analytic_debit_acc_id=(company.provision_pl_analytic_account_id.id),
                )
                created_ids.extend(line_ids)

        return created_ids

    def _validate_company_revaluation_configuration(self, company):
        return (
            (
                company.revaluation_loss_account_id
                and company.revaluation_gain_account_id
            )
            or (
                company.provision_bs_loss_account_id
                and company.provision_pl_loss_account_id
            )
            or (
                company.provision_bs_gain_account_id
                and company.provision_pl_gain_account_id
            )
        )

    def revaluate_currency(self):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """

        Account = self.env["account.account"]
        Currency = self.env["res.currency"]

        company = self.journal_id.company_id or self.env.company
        if not self._validate_company_revaluation_configuration(company):
            raise exceptions.UserError(
                _(
                    "No revaluation or provision account are defined"
                    " for your company.\n"
                    "You must specify at least one provision account or"
                    " a couple of provision account in the accounting settings."
                )
            )

        account_ids = self.revaluation_account_ids

        if not account_ids:
            raise exceptions.UserError(
                _(
                    "No account to be revaluated found. "
                    "Please check 'Allow Currency Revaluation' "
                    "for at least one account in account form."
                )
            )

        revaluations = account_ids.compute_revaluations(
            self.revaluation_date, self.start_date
        )

        for account_id, by_account in revaluations.items():
            account = Account.browse(account_id)
            if account.internal_type == "liquidity" and (
                not account.currency_id
                or account.currency_id == account.company_id.currency_id
            ):
                # NOTE: There's no point of revaluating anything on bank account
                # if bank account currency matches company currency.
                continue

            for partner_id, by_partner in by_account.items():
                for currency_id, lines in by_partner.items():
                    currency = Currency.browse(currency_id).with_context(
                        date=self.revaluation_date
                    )

                    diff_balances = self._compute_unrealized_currency_gl(
                        currency, lines
                    )
                    revaluations[account_id][partner_id][currency_id].update(
                        diff_balances
                    )

        # Create entries only after all computation have been done
        created_ids = []
        for account_id, by_account in revaluations.items():
            account = Account.browse(account_id)

            for partner_id, by_partner in by_account.items():
                for currency_id, lines in by_partner.items():
                    currency = Currency.browse(currency_id)

                    adj_balance = lines.get("unrealized_gain_loss", 0.0)
                    if currency.is_zero(adj_balance):
                        continue
                    rate = lines.get("currency_rate", 0.0)
                    label = self._format_balance_adjustment_label(
                        self.label, account, currency, rate
                    )

                    new_ids = self._write_adjust_balance(
                        account, currency, partner_id, adj_balance, label, self, lines
                    )
                    created_ids.extend(new_ids)

        if created_ids:
            return {
                "domain": [("id", "in", created_ids)],
                "name": _("Created Revaluation Lines"),
                "view_mode": "tree,form",
                "auto_search": True,
                "res_model": "account.move.line",
                "view_id": False,
                "search_view_id": False,
                "type": "ir.actions.act_window",
            }
        else:
            raise exceptions.UserError(_("No accounting entry has been posted."))
