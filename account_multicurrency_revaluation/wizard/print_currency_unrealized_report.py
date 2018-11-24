# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class UnrealizedCurrencyReportPrinter(models.TransientModel):
    _name = "unrealized.report.printer"
    _description = 'Unrealized Currency Report Printer'

    account_ids = fields.Many2many(
        'account.account',
        string='Accounts',
        domain="[('currency_revaluation', '=', True)]",
        default=lambda self: self._default_account_ids(),
    )

    def _default_account_ids(self):
        account_model = self.env["account.account"]
        account_ids = account_model.search([
            ('currency_revaluation', '=', True)
        ]).ids
        return [(6, 0, account_ids)]

    @api.multi
    def print_report(self, data):
        """
        Show the report
        """
        if self.account_ids:
            docids = self.account_ids.ids
            # in Odoo 11 we no longer call render, but report_action
            # config should be false as otherwise it will call configuration
            # wizard that works weirdly
            return self.env.ref(
                'account_multicurrency_revaluation.'
                'action_report_currency_unrealized'
            ).report_action(docids, config=False)
        else:
            raise ValidationError(_("Please, select the accounts!"))
