# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Cut-off Prepaid',
    'version': '10.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Prepaid Expense, Prepaid Revenue',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_cutoff_base',
        'account_invoice_start_end_dates',
        ],
    'data': [
        'views/company.xml',
        'views/account_cutoff.xml',
    ],
    'images': [
        'images/prepaid_revenue_draft.jpg',
        'images/prepaid_revenue_journal_entry.jpg',
        'images/prepaid_revenue_done.jpg',
        ],
    'installable': True,
}
