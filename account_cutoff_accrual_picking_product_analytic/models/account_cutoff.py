# -*- coding: utf-8 -*-
# Copyright 2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def _get_expense_analytic(self, line):
        analytics = line.product_id.product_tmpl_id._get_product_analytic_accounts()
        analytic = analytics["expense"]
        return analytic

    def _get_revenue_analytic(self, line):
        analytics = line.product_id.product_tmpl_id._get_product_analytic_accounts()
        analytic = analytics["income"]
        return analytic
