# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{"name": "Multicurrency Revaluation Report",
 "version": "9.0.1.0.0",
 "category": "Finance",
 "author": "Camptocamp,Odoo Community Association (OCA)",
 "license": 'AGPL-3',
 "summary": "Module for printing reports that completes the module "
            "Multicurrency Revaluation",
 "depends": [
     "account_multicurrency_revaluation",
     "report",
 ],
 "data": [
     "wizard/print_currency_unrealized_report_view.xml",
     "report/report.xml",
     "report/unrealized_currency_gain_loss.xml"
 ],
 'installable': True,
 }
