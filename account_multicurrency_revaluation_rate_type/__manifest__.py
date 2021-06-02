# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Multicurrency revaluation with monthly currency rates",
    "version": "12.0.1.0.3",
    "category": "Finance",
    "summary": "Use monthly currency rate for multicurrency revaluation",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-closing",
    "license": 'AGPL-3',
    "depends": [
        "account_multicurrency_revaluation",
        "currency_monthly_rate",
    ],
    "demo": [
    ],
    "data": [
        "views/res_config_view.xml",
        "wizard/wizard_currency_revaluation_view.xml",
    ],
    'installable': True,
}
