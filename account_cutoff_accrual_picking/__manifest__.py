# Copyright 2013-2019 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Cut-off Accrual Picking',
    'version': '12.0.1.0.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'summary': 'Accrued expense & accrued revenue from pickings',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/account-closing',
    'depends': ['account_cutoff_accrual_base', 'purchase', 'sale_stock'],
    'images': [
        'images/accrued_expense_draft.jpg',
        'images/accrued_expense_journal_entry.jpg',
        'images/accrued_expense_done.jpg',
        ],
    'installable': True,
    'application': True,
}
