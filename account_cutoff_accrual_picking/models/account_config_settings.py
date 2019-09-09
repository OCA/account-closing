# -*- coding: utf-8 -*-
# Copyright 2019 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    default_accrual_picking_backward_days = fields.Integer(
        related='company_id.default_accrual_picking_backward_days')
