# -*- coding: utf-8 -*-
# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class WizardCurrencyRevaluationType(models.TransientModel):

    _inherit = 'wizard.currency.revaluation'

    @api.model
    def _get_default_rate_type(self):
        # Get default currency rate type if one is defined in company settings
        return self.env.user.company_id.revaluation_rate_type

    revaluation_rate_type = fields.Selection(
        string='Rate type',
        selection=[
            ('average', 'Monthly Average'),
            ('daily', 'Daily'),
        ],
        default=lambda self: self._get_default_rate_type(),
    )

    @api.model
    def _compute_unrealized_currency_gl(self, currency_id, balances, form):
        if self.revaluation_rate_type == 'average':
            self = form.with_context(monthly_rate=True)
        return super(WizardCurrencyRevaluationType, self).\
            _compute_unrealized_currency_gl(currency_id, balances, self)
