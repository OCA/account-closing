# Copyright (C) 2013 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2018 Camptcamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    'name': 'Account Accrual Base',
    'version': '11.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Base module for accrued expenses and revenues',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/account-closing',
    'depends': [
        'account_cutoff_base',
    ],
    'data': [
        'views/company_view.xml',
        'views/account_view.xml',
        'views/account_cutoff_view.xml',
    ],
    'installable': True,
}
