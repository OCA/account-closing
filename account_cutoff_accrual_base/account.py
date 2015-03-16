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


class account_tax(orm.Model):
    _inherit = 'account.tax'

    _columns = {
        'account_accrued_revenue_id': fields.many2one(
            'account.account', 'Accrued Revenue Tax Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')]),
        'account_accrued_expense_id': fields.many2one(
            'account.account', 'Accrued Expense Tax Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')]),
    }
