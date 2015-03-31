# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher
#    Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Multicurrency revaluation report",
    "version": "8.0",
    "category": "Finance",
    "description": """
===========================
 Multicurrency revaluation
===========================

The *Multicurrency revaluation report* completes the module *Multicurrency
revaluation* by providing a Revaluation report.

---------------
 Main Features
---------------

* A wizard to print a report of revaluation.

The report uses webkit report system.

""",

    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": 'AGPL-3',
    "depends": [
        "account_multicurrency_revaluation",
        "base_headers_webkit"
    ],
    "data": [
        "wizard/print_currency_unrealized_report_view.xml",
        "report/report.xml",
    ],
    'installable': False,
}
