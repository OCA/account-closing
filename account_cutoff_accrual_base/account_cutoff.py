# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Accrual Base module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv import orm, fields
import openerp.addons.decimal_precision as dp


class account_cutoff(orm.Model):
    _inherit = 'account.cutoff'

    def _inherit_default_cutoff_account_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        account_id = super(account_cutoff, self).\
            _inherit_default_cutoff_account_id(
                cr, uid, context=context)
        type = context.get('type')
        company = self.pool['res.users'].browse(
            cr, uid, uid, context=context).company_id
        if type == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif type == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id


class account_cutoff_line(orm.Model):
    _inherit = 'account.cutoff.line'

    _columns = {
        'quantity': fields.float(
            'Quantity', digits_compute=dp.get_precision('Product UoS'),
            readonly=True),
        'price_unit': fields.float(
            'Unit Price', digits_compute=dp.get_precision('Product Price'),
            readonly=True, help="Price per unit (discount included)"),
    }
