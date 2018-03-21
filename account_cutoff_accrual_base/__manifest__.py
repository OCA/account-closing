# -*- coding: utf-8 -*-
# Copyright 2013-2018 Akretion
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Accrual Base',
    'version': '10.0.1.1.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'summary': 'Base module for accrued expenses and revenues',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['account_cutoff_base'],
    'data': [
        'views/account_config_settings.xml',
        'views/account_tax.xml',
        'views/account_cutoff_view.xml',
    ],
    'installable': True,
}
