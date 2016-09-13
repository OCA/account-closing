# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Accrual Base',
    'version': '8.0.0.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Base module for accrued expenses and revenues',
    'description': """This module contains objets, fields and menu entries that are used by other accrual modules. So you need to install other accrual modules to get the additionnal functionalities :
- the module 'account_cutoff_accrual_picking' will manage accrued expenses and revenues based on pickings.
- a not-developped-yet module will manage accrued expenses and revenues based on timesheets.

This module has been written by Alexis de Lattre from Akretion <alexis.delattre@akretion.com>.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['account_cutoff_base'],
    'data': [
        'views/company.xml',
        'views/account_tax.xml',
        'views/account_cutoff.xml',
    ],
    'installable': True,
}
