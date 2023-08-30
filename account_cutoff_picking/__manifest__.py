# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


{
    "name": "Account Cut-off Picking",
    "version": "16.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Accrued Expense & Accrued Revenue from Pickings",
    "author": "BCIM, Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_base", "purchase", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_cutoff_view.xml",
        "data/ir_cron.xml",
    ],
    "images": [
        "images/accrued_expense_draft.jpg",
        "images/accrued_expense_journal_entry.jpg",
        "images/accrued_expense_done.jpg",
    ],
    "installable": True,
    "application": True,
}
