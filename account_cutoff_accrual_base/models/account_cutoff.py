# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _inherit_default_cutoff_account_id(self):
        account_id = super(AccountCutoff, self).\
            _inherit_default_cutoff_account_id()
        type = self._context.get('type')
        company = self.env.user.company_id
        if type == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif type == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    @api.multi
    def generate_accrual_lines(self):
        """This method is inherited by the modules that depend on this one"""
        self.ensure_one()
        self.line_ids.unlink()
        return True


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    quantity = fields.Float(
        string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
        readonly=True)
    price_unit = fields.Float(
        string='Unit Price',
        digits=dp.get_precision('Product Price'), readonly=True,
        help="Price per unit without taxes (discount included)")
    price_source = fields.Selection([
        ('sale', 'Sale Order'),
        ('purchase', 'Purchase Order'),
        ('invoice', 'Invoice'),
        ], string='Price Source', readonly=True)
