# Copyright 2012-2018 Camptocamp SA
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnrealizedCurrencyReportPrinter(models.TransientModel):
    _name = "unrealized.report.printer"
    _description = "Unrealized Currency Report Printer"

    account_ids = fields.Many2many(
        "account.account",
        string="Accounts",
        domain=[("currency_revaluation", "=", True)],
        default=lambda self: self._default_account_ids(),
    )
    start_date = fields.Date(
        help="The report will print from this Date, all the revaluated entries"
        " created from this date. The default value will be the first day of the month",
        default=lambda self: self._default_start_date(),
    )
    end_date = fields.Date(
        help="The report will print till this Date. The default value will be today.",
        required=True,
        default=lambda self: self._default_end_date(),
    )
    only_include_posted_entries = fields.Boolean(
        default=False,
    )

    def _default_account_ids(self):
        account_model = self.env["account.account"]
        company = self.env.company
        account_ids = account_model.search(
            [("currency_revaluation", "=", True), ("company_id", "=", company.id)]
        ).ids
        return [(6, 0, account_ids)]

    @api.onchange("start_date", "end_date")
    def _onchange_dates(self):
        self.ensure_one()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise UserError(_("The Start Date cannot be higher than the End Date."))

    def _default_start_date(self):
        return fields.Date.today().replace(day=1)

    def _default_end_date(self):
        return fields.Date.today()

    def print_report(self):
        """
        Show the report
        """
        if self.account_ids:
            data = {
                "start_date": self.start_date,
                "end_date": self.end_date,
                "only_include_posted_entries": self.only_include_posted_entries,
                "account_ids": self.account_ids.ids,
            }
            # report_action config should be false, otherwise it will call
            # configuration wizard that works weirdly
            return self.env.ref(
                "account_multicurrency_revaluation.action_report_currency_unrealized"
            ).report_action(docids=[], data=data, config=False)
        else:
            raise ValidationError(_("Please, select the accounts!"))
