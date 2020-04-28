# Copyright 2013-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Accrual Base",
    "version": "13.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Base module for accrued expenses and revenues",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_base"],
    "data": [
        "views/res_config_settings.xml",
        "views/account_tax.xml",
        "views/account_cutoff_view.xml",
    ],
    "installable": True,
}
