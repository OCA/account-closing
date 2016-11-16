# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    must_have_dates = fields.Boolean(
        string='Must Have Start and End Dates',
        help="If this option is active, the user will have to enter "
        "a Start Date and an End Date on the invoice lines that have "
        "this product.")
