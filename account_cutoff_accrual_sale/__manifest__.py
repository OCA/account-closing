# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Account Cut-off Accrual Sale",
    "version": "16.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Accrued Revenue on Sales Order",
    "author": "BCIM, Odoo Community Association (OCA)",
    "maintainers": ["jbaudoux"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_accrual_order_base", "sale", "sale_force_invoiced"],
    "data": [
        "views/account_cutoff.xml",
        "views/account_cutoff_line.xml",
        "data/ir_cron.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}
