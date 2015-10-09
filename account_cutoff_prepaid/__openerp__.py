# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid module for OpenERP
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


{
    'name': 'Account Cut-off Prepaid',
    'version': '8.0.0.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Prepaid Expense, Prepaid Revenue',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['account_cutoff_base'],
    'data': [
        'company_view.xml',
        'product_view.xml',
        'account_invoice_view.xml',
        'account_view.xml',
        'account_cutoff_view.xml',
    ],
    'demo': ['product_demo.xml'],
    'images': [
        'images/prepaid_revenue_draft.jpg',
        'images/prepaid_revenue_journal_entry.jpg',
        'images/prepaid_revenue_done.jpg',
    ],
    'installable': True,
    'active': False,
    'application': True,
}
