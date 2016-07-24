# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Cut-off Base',
    'version': '9.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Base module for Account Cut-offs',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': ['account_accountant'],
    'data': [
        'security/account_cutoff_base_security.xml',
        'security/ir.model.access.csv',
        'views/company.xml',
        'views/account_cutoff.xml',
    ],
    'installable': True,
}
