# Copyright 2019-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    subscription_id = fields.Many2one(
        "account.cutoff.accrual.subscription", ondelete="restrict", check_company=True
    )
