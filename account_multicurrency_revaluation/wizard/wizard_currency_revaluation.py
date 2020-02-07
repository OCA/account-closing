# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import Warning as UserError


class WizardCurrencyRevaluation(models.TransientModel):

    _name = "wizard.currency.revaluation"
    _description = "Currency Revaluation Wizard"

    @api.model
    def _get_default_revaluation_date(self):
        """
        Get today's date
        """
        return fields.date.today()

    @api.model
    def _get_default_journal_id(self):
        """
        Get default journal if one is defined in company settings
        """
        return self.env.user.company_id.currency_reval_journal_id

    @api.model
    def _get_default_label(self):
        """
        Get label
        """
        return "%(currency)s %(account)s %(rate)s currency revaluation"

    revaluation_date = fields.Date(
        string="Revaluation Date",
        required=True,
        default=lambda self: self._get_default_revaluation_date(),
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('type','=','general')]",
        help="You can set the default journal in company settings.",
        required=True,
        default=lambda self: self._get_default_journal_id(),
    )
    label = fields.Char(
        string="Entry description",
        size=100,
        help="This label will be inserted in entries description. "
        "You can use %(account)s, %(currency)s and %(rate)s keywords.",
        required=True,
        default=lambda self: self._get_default_label(),
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
    ):

        base_move = {"journal_id": form.journal_id.id, "date": form.revaluation_date}
        if form.journal_id.company_id.reversable_revaluations:
            base_move["revaluation_to_reverse"] = True

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

        debit_line = base_line.copy()
        credit_line = base_line.copy()

        debit_line.update(
            {"debit": amount, "credit": 0.0, "account_id": debit_account_id}
        )

        if analytic_debit_acc_id:
            credit_line.update({"analytic_account_id": analytic_debit_acc_id})

        credit_line.update(
            {"debit": 0.0, "credit": amount, "account_id": credit_account_id}
        )

        if analytic_credit_acc_id:
            credit_line.update({"analytic_account_id": analytic_credit_acc_id})
        base_move["line_ids"] = [(0, 0, debit_line), (0, 0, credit_line)]
        created_move = self.env["account.move"].create(base_move)
        created_move.post()
        return [x.id for x in created_move.line_ids]

    def _compute_unrealized_currency_gl(self, currency_id, balances):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation

        @param int currency_id: currency to revaluate
        @param dict balances: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        currency_obj = self.env["res.currency"]

        # Compute unrealized gain loss
        cp_currency = self.journal_id.company_id.currency_id

        currency = currency_obj.browse(currency_id).with_context(
            date=self.revaluation_date
        )

        foreign_balance = adjusted_balance = balances.get("foreign_balance", 0.0)
        balance = balances.get("balance", 0.0)
        unrealized_gain_loss = 0.0
        if foreign_balance:
            adjusted_balance = currency._convert(
                foreign_balance, cp_currency, self.env.company, self.revaluation_date
            )
            unrealized_gain_loss = adjusted_balance - balance
        else:
            if balance:
                if currency_id != cp_currency.id:
                    unrealized_gain_loss = 0.0 - balance
        return {
            "unrealized_gain_loss": unrealized_gain_loss,
            "currency_rate": currency.rate,
            "revaluated_balance": adjusted_balance,
        }

    @api.model
    def _format_label(self, text, account_id, currency_id, rate):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param int currency_id: id of the currency to display
        @param float rate: rate to display
        """
        account_obj = self.env["account.account"]
        currency_obj = self.env["res.currency"]
        account = account_obj.browse(account_id)
        currency = currency_obj.browse(currency_id)
        data = {
            "account": account.code or False,
            "currency": currency.name or False,
            "rate": rate,
        }
        return text % data

    def _write_adjust_balance(
        self, account_id, currency_id, partner_id, amount, label, form, sums
    ):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """

        if partner_id is None:
            partner_id = False
        company = form.journal_id.company_id or self.env.user.company_id
        created_ids = []
        # over revaluation
        if amount >= 0.01:
            reval_gain_account = company.revaluation_gain_account_id
            if reval_gain_account:

                analytic_acc_id = (
                    company.revaluation_analytic_account_id.id
                    if company.revaluation_analytic_account_id
                    else False
                )

                line_ids = self._create_move_and_lines(
                    amount,
                    account_id,
                    reval_gain_account.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency_id,
                    analytic_credit_acc_id=analytic_acc_id,
                )

                created_ids.extend(line_ids)

            if (
                company.provision_bs_gain_account_id
                and company.provision_pl_gain_account_id
            ):

                analytic_acc_id = (
                    company.provision_pl_analytic_account_id
                    and company.provision_pl_analytic_account_id.id
                    or False
                )

                line_ids = self._create_move_and_lines(
                    amount,
                    company.provision_bs_gain_account_id.id,
                    company.provision_pl_gain_account_id.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency_id,
                    analytic_credit_acc_id=analytic_acc_id,
                )

                created_ids.extend(line_ids)

        # under revaluation
        elif amount <= -0.01:
            amount = -amount
            reval_loss_account = company.revaluation_loss_account_id
            if reval_loss_account:

                analytic_acc_id = (
                    company.revaluation_analytic_account_id.id
                    if company.revaluation_analytic_account_id
                    else False
                )

                line_ids = self._create_move_and_lines(
                    amount,
                    reval_loss_account.id,
                    account_id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency_id,
                    analytic_debit_acc_id=analytic_acc_id,
                )

                created_ids.extend(line_ids)

            if (
                company.provision_bs_loss_account_id
                and company.provision_pl_loss_account_id
            ):

                analytic_acc_id = (
                    company.provision_pl_analytic_account_id
                    and company.provision_pl_analytic_account_id.id
                    or False
                )

                line_ids = self._create_move_and_lines(
                    amount,
                    company.provision_pl_loss_account_id.id,
                    company.provision_bs_loss_account_id.id,
                    sums,
                    label,
                    form,
                    partner_id,
                    currency_id,
                    analytic_debit_acc_id=analytic_acc_id,
                )

                created_ids.extend(line_ids)

        return created_ids

    @staticmethod
    def _check_company(company):
        return (
            not company.revaluation_loss_account_id
            and not company.revaluation_gain_account_id
            and not (
                company.provision_bs_loss_account_id
                and company.provision_pl_loss_account_id
            )
            and not (
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

        account_obj = self.env["account.account"]

        company = self.journal_id.company_id or self.env.user.company_id
        if self._check_company(company):
            raise UserError(
                _(
                    "No revaluation or provision account are defined"
                    " for your company.\n"
                    "You must specify at least one provision account or"
                    " a couple of provision account in the accounting settings."
                )
            )
        created_ids = []
        # Search for accounts Balance Sheet to be revaluated
        # on those criteria
        # - deferral method of account type is not None
        account_ids = account_obj.search(
            [
                ("user_type_id.include_initial_balance", "=", "True"),
                ("currency_revaluation", "=", True),
            ]
        )

        if not account_ids:
            raise UserError(
                _(
                    "No account to be revaluated found. "
                    "Please check 'Allow Currency Revaluation' "
                    "for at least one account in account form."
                )
            )

        # Get balance sums
        account_sums = account_ids.compute_revaluations(self.revaluation_date)

        for account_id, account_tree in account_sums.items():
            for partner_id, partner_tree in account_tree.items():
                for currency_id, sums in partner_tree.items():
                    # Update sums with compute amount currency balance
                    diff_balances = self._compute_unrealized_currency_gl(
                        currency_id, sums
                    )
                    account_sums[account_id][partner_id][currency_id].update(
                        diff_balances
                    )

        # Create entries only after all computation have been done
        for account_id, account_tree in account_sums.items():
            for partner_id, partner_tree in account_tree.items():
                for currency_id, sums in partner_tree.items():
                    adj_balance = sums.get("unrealized_gain_loss", 0.0)
                    if not adj_balance:
                        continue
                    account_type = account_obj.browse(account_id).internal_type
                    if account_type not in ["receivable", "payable"]:
                        partner_id = None
                    rate = sums.get("currency_rate", 0.0)
                    label = self._format_label(
                        self.label, account_id, currency_id, rate
                    )

                    # Write an entry to adjust balance
                    new_ids = self._write_adjust_balance(
                        account_id,
                        currency_id,
                        partner_id,
                        adj_balance,
                        label,
                        self,
                        sums,
                    )
                    created_ids.extend(new_ids)

        if created_ids:
            return {
                "domain": "[('id', 'in', %s)]" % created_ids,
                "name": _("Created revaluation lines"),
                "view_mode": "tree,form",
                "auto_search": True,
                "res_model": "account.move.line",
                "view_id": False,
                "search_view_id": False,
                "type": "ir.actions.act_window",
            }
        else:
            raise UserError(_("No accounting entry has been posted."))
