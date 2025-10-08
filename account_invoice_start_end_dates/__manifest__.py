# Copyright 2016-2021 Akretion France (http://www.akretion.com/)
# Copyright 2018-2021 Camptocamp
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Account Invoice Start End Dates",
    "version": "18.0.1.2.0",
    "category": "Accounting & Finance",
    "license": "LGPL-3",
    "summary": "Adds start/end dates on invoice/move lines",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account"],
    "data": [
        "views/account_move.xml",
        "views/account_move_line.xml",
        "views/product_template.xml",
        "reports/account_invoice_report_view.xml",
    ],
    "demo": ["demo/product_demo.xml"],
    "installable": True,
}
