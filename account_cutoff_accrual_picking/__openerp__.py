# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Accrual Picking',
    'version': '0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Accrued Expense & Accrued Revenue from Pickings',
    'description': """
Manage expense and revenue accruals from pickings
=================================================

This module generates expense and revenue accruals based on the invoices linked to pickings.

For revenue accruals, Odoo will take into account all the customer invoices (including draft invoices) that have an invoice date after the cut-off date (or, for a draft invoice, that have no invoice date) that are linked to pickings in *Delivered* state that have been shipped before the cut-off date.

The logic is the same for expense accruals, using supplier invoices instead of customer invoices.

The current code of the module only works when :

* on sale orders, the *Create Invoice* field is set to *On Delivery Order* ;
* for purchase orders, the *Invoicing Control* field is set to *Based on incoming shipments*.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_cutoff_accrual_base',
        'stock_picking_invoice_link',
        ],
    'data': [
        'account_cutoff_view.xml',
    ],
    'images': [
        'images/accrued_expense_draft.jpg',
        'images/accrued_expense_journal_entry.jpg',
        'images/accrued_expense_done.jpg',
        ],
    'installable': True,
    'application': True,
}
