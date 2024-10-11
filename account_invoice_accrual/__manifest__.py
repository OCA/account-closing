# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account invoice accrual",
    "version": "16.0.1.0.0",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "category": "Invoice",
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_base"],
    "data": [
        "security/account_move_accrue.xml",
        "wizards/res_config_settings.xml",
        "wizards/account_move_accrue.xml",
        "views/account_move.xml",
    ],
    "demo": [],
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
