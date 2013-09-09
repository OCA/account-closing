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


from openerp.osv import osv, fields

class res_company(osv.Model):
    _inherit = 'res.company'

    _columns = {
        'default_accrued_revenue_account_id': fields.many2one('account.account',
            'Default Account for Accrued Revenues',
            domain=[('type','<>','view')]), # FR : 418100
        'default_accrued_expense_account_id': fields.many2one('account.account',
            'Default Account for Accrued Expenses',
            domain=[('type','<>','view')]), # FR : 408100
    }
