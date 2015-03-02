# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Accrual Picking module for OpenERP
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
    'name': 'Account Accrual Picking',
    'version': '0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Accrued Expense & Accrued Revenue from Pickings',
    'description': """
Manage expense and revenue accruals from pickings
=================================================

This module generates expense and revenue accruals based on the status of
pickings.

For revenue accruals, OpenERP will take into account all the delivery orders
in *Delivered* state that have been shipped before the cut-off date and that
have *Invoice Control* = *To Be Invoiced*.

For expense accruals, OpenERP will take into account all the incoming
shipments in *Received* state that have been received before the cut-off date
and that have *Invoice Control* = *To Be Invoiced*.

The current code of the module only works when :

* on sale orders, the *Create Invoice* field is set to *On Delivery Order* ;
* for purchase orders, the *Invoicing Control* field is set to *Based on
incoming shipments*.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com>
for any help or question about this module.
    """,
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['account_cutoff_accrual_base', 'purchase', 'sale_stock'],
    'data': [
        'account_cutoff_view.xml',
    ],
    'images': [
        'images/accrued_expense_draft.jpg',
        'images/accrued_expense_journal_entry.jpg',
        'images/accrued_expense_done.jpg',
        ],
    'installable': False,
    'active': False,
    'application': True,
}
