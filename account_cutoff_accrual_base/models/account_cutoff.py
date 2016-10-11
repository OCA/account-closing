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

    def _get_default_journal(self, cr, uid, context=None):
        journal_id = super(AccountCutoff, self)\
            ._get_default_journal(cr, uid, context=context)
        cur_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        cutoff_type = context.get('type', False)
        default_journal_id = cur_user.company_id\
            .default_cutoff_journal_id.id or False
        if cutoff_type == 'accrued_expense':
            journal_id =\
                cur_user.company_id.default_accrual_expense_journal_id.id or\
                default_journal_id
        elif cutoff_type == 'accrued_revenue':
            journal_id = \
                cur_user.company_id.default_accrual_revenue_journal_id.id or\
                default_journal_id
        return journal_id


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
