# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Accrual Picking',
    'version': '8.0.0.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Accrued Expense & Accrued Revenue from Pickings',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_cutoff_accrual_base',
        'stock_picking_invoice_link',
        'purchase',
        'sale_stock',
        ],
    'data': [
        'views/account_cutoff.xml',
    ],
    'images': [
        'images/accrued_expense_draft.jpg',
        'images/accrued_expense_journal_entry.jpg',
        'images/accrued_expense_done.jpg',
        ],
    'installable': True,
    'application': True,
}
