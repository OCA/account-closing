# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Invoice Start End Dates',
    'version': '9.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Adds start/end dates on invoice lines and move lines',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': ['account'],
    'data': [
        'views/account_invoice.xml',
        'views/account_move.xml',
        'views/product.xml',
    ],
    'demo': ['demo/product_demo.xml'],
    'installable': True,
}
