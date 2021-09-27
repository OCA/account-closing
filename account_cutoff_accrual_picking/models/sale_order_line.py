# -*- coding: utf-8 -*-
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    account_cutoff_line_ids = fields.One2many(
        'account.cutoff.line', 'sale_line_id',
        string='Account Cutoff Lines',
        readonly=True)
