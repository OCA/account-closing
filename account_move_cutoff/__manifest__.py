# Copyright 2022 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Move Cut-off",
    "version": "14.0.0.0.1",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Account move Cut-offs, manage Deferred Revenues/Expenses",
    "author": "Pierre Verkest <pierreverkest84@gmail.com>, Odoo Community Association (OCA)",
    "maintainers": ["petrus-v"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account", "account_invoice_start_end_dates"],
    "data": [
        "views/account_account.xml",
        "views/account_move_line.xml",
        "views/account_move.xml",
        "views/res_config_settings.xml",
    ],
    "installable": True,
}
