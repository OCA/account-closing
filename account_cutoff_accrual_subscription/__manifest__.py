# Copyright 2019-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Accrual Subscriptions",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Accrued expenses based on subscriptions",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_start_end_dates"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/account_cutoff_accrual_subscription.xml",
    ],
    "installable": True,
}
