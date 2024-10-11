# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Account Cut-off Accrual Sale Stock",
    "version": "16.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Glue module for Cut-Off Accruals on Sales with Stock Deliveries",
    "author": "BCIM, Odoo Community Association (OCA)",
    "maintainers": ["jbaudoux"],
    "website": "https://github.com/OCA/account-closing",
    "depends": [
        "account_cutoff_accrual_sale",
        "account_cutoff_accrual_order_stock_base",
        "sale_stock",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
}
