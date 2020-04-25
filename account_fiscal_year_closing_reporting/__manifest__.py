# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fiscal year closing reporting",
    "summary": "Remove fyc moves from account reporting",
    "version": "12.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://efatto.it/",
    "author": "Sergio Corato, "
              "Odoo Community Association (OCA)",
    "maintainers": ["sergiocorato"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_fiscal_year_closing",
        "account_financial_report",
    ],
    "data": [
        'wizard/general_ledger_wizard_view.xml',
    ],
    "auto_install": True,
}
