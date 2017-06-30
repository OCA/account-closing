# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{"name": "Multicurrency revaluation",
 "version": "9.0.1.0.0",
 "category": "Finance",
 "summary": "Manage revaluation for multicurrency environment",
 "author": "Camptocamp,Odoo Community Association (OCA)",
 "license": 'AGPL-3',
 "depends": [
     "account_reversal",
 ],
 "demo": [
     "demo/currency_demo.xml",
     "demo/account_demo.xml",
 ],
 "data": [
     "views/res_config_view.xml",
     "security/security.xml",
     "views/account_view.xml",
     "wizard/wizard_currency_revaluation_view.xml"
 ],
 "tests": [
     "tests/test_currency_revaluation.py",
 ],
 'installable': True,
 }
