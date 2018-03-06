# -*- coding: utf-8 -*-
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    accrued_supplier_return = fields.Boolean(
        'Accrued Supplier Return')
    accrued_customer_return = fields.Boolean(
        'Accrued Customer Return')
