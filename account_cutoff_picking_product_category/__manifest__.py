# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Cutoff Picking Product Category",
    "summary": """
        Allows to get the product category on cutoff lines""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,BCIM,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_picking", "account_move_line_product_category"],
    "data": [
        "views/account_cutoff_line.xml",
    ],
}
