# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account invoice accrual",
    "version": "10.0.1.0.0",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "category": "Invoice",
    "website": "http://www.acsone.eu",
    "depends": [
        "account",
        "account_reversal",
        "account_cutoff_accrual_base",
    ],
    "data": [
        "views/account_invoice_view.xml",
        "wizard/account_move_accrue_view.xml",
    ],
    "demo": [],
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
