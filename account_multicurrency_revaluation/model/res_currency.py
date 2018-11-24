# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class ResCurrency(models.Model):

    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        context = self.env.context
        if not context.get('revaluation'):
            return super()._get_conversion_rate(from_currency, to_currency,
                                                company, date)
        return 1.0 / from_currency.rate
