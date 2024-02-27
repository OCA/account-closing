# Copyright 2023 Sergio Corato
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account invoice start end dates on invoice",
    "summary": "Add the possibility to choose start and end dates on account invoice.",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Accounting & Finance",
    "website": "https://github.com/OCA/account-closing",
    "author": "Sergio Corato, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account_invoice_start_end_dates"],
    "data": [
        "views/account_move.xml",
        "views/res_config_settings.xml",
    ],
}
