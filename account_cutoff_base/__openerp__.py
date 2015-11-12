# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Base module for OpenERP
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
    'name': 'Account Cut-off Base',
    'version': '8.0.0.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Base module for Account Cut-offs',
    'description': """
This module contains objets, fields and menu entries that are used by other
cut-off modules. So you need to install other cut-off modules to get the
additionnal functionalities :

* the module *account_cutoff_prepaid* will manage prepaid cut-offs based on
  start date and end date,
* the module *account_cutoff_accrual_picking* will manage the accruals based
  on the status of the pickings.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com>
for any help or question about this module.
    """,
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': [
        'account_accountant',
        'account_reversal',
    ],
    'data': [
        'company_view.xml',
        'account_cutoff_view.xml',
        'security/ir.model.access.csv',
        'security/account_cutoff_base_security.xml',
    ],
    'installable': True,
    'active': False,
}
