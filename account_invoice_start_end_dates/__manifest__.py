# Copyright 2016-2019 Akretion France
# Copyright 2018-2019 Camptocamp
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Invoice Start End Dates",
    "version": "13.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Adds start/end dates on invoice/move lines",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account"],
    "data": ["views/account_move.xml", "views/product.xml"],
    "demo": ["demo/product_demo.xml"],
    "installable": True,
}
