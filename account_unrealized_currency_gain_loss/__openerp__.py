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

{"name": "Unrealized currency gain & loss",
 "version": "6.1",
 "category": "Finance",
 "description": """
=================================
 Unrealized currency gain & loss
=================================

The Unrealized currency gain & loss provides wizards to revaluate and get a report on revaluation.

It supports different type of writing the gain & loss like UK Revaluation or CH provisioning.


---------------
 Main Features
---------------

Adds two wizards to:

* Generate the unrealized currency gain & loss entries. It adjusts accounts' balance of account with a foreign currency.
* Print a report of unrealized gain & loss.

The report uses webkit report system.

---------------
 Configuration
---------------

To configure it, *Foreign currency gain & loss* accounts have been added in company parameters.

For UK (Revaluation)
====================

::

                        LOSS  GAIN
  Revaluation account    [x]  [x]
  Provision B.S account  [ ]  [ ]
  Provision P&L account  [ ]  [ ]

For CH (Provision)
==================

::

                        LOSS  GAIN
  Revaluation account    [ ]  [ ]
  Provision B.S account  [x]  [ ]
  Provision P&L account  [x]  [ ]

For FR
======

::

                        LOSS  GAIN
  Revaluation account    [x]  [x]
  Provision B.S account  [x]  [ ]
  Provision P&L account  [x]  [ ]
""",

    "author": "Camptocamp",
    "license": 'AGPL-3',
    "depends": ["base",
                "account",
                "account_reversal",
                "base_headers_webkit"],
    "init_xml": ["res_company_view.xml",
                 "res_currency_view.xml",
                 "account_view.xml",
                 "wizard/wizard_currency_revaluation_view.xml",
                 "wizard/print_currency_unrealized_report_view.xml"],
    "update_xml": ['report/report.xml'],
    #"test": ["test/currency_revaluation.yml"],
    "demo_xml": [],
    'installable': True,
    "active": False,
#    'certificate': 'certificate',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
