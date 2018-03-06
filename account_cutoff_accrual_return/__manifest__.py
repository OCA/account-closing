# -*- coding: utf-8 -*-
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Accrual Return Picking',
    'version': '10.0.0.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Accrued Expense & Accrued Revenue from Return Pickings',
    'author': "BCIM,Odoo Community Association (OCA)",
    'depends': ['account_cutoff_accrual_base', 'stock'],
    'data': [
        'views/account_cutoff.xml',
        'views/stock_location.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': True,
}
