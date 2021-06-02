# Copyright 2019 Camptocamp SA
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class WizardCurrencyRevaluationType(models.TransientModel):

    _inherit = 'wizard.currency.revaluation'

    @api.model
    def _default_revaluation_rate_type(self):
        """
        Get default rate type if one is defined in company settings
        """
        return self.env.user.company_id.revaluation_rate_type

    revaluation_rate_type = fields.Selection(
        string='Rate type',
        selection=[
            ('monthly', 'Monthly Average'),
            ('daily', 'Daily'),
        ],
        default=lambda self: self._default_revaluation_rate_type(),
    )

    @api.model
    def _compute_unrealized_currency_gl(self, currency, balances):
        if self.revaluation_rate_type == 'monthly':
            currency = currency.with_context(monthly_rate=True)
        return super()._compute_unrealized_currency_gl(currency, balances)
