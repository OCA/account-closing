# Copyright 2016-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2018-2022 CampToCamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Cut-off Start End Dates",
    "version": "16.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Cutoffs based on start/end dates",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_base", "account_invoice_start_end_dates"],
    "data": [
        "views/account_cutoff.xml",
        "views/account_cutoff_line.xml",
    ],
    "images": [
        "images/prepaid_revenue_draft.jpg",
        "images/prepaid_revenue_journal_entry.jpg",
        "images/prepaid_revenue_done.jpg",
    ],
    "installable": True,
    "application": True,
}
