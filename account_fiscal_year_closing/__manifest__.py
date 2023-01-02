# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fiscal year closing",
    "summary": "Generic fiscal year closing wizard",
    "version": "12.0.1.0.1",
    "category": "Accounting & Finance",
    "website": "https://github.com/OCA/account-closing",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account",
    ],
    "data": [
        "security/account_fiscalyear_closing_security.xml",
        "security/ir.model.access.csv",
        "views/account_fiscalyear_closing_views.xml",
        "views/account_fiscalyear_closing_template_views.xml",
        "views/account_move_views.xml",
        "wizards/account_fiscal_year_closing_unbalanced_move_views.xml",
    ],
}
