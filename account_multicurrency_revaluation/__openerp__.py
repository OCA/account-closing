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

{"name": "Multicurrency revaluation",
 "version": "6.1",
 "category": "Finance",
 "description": """
===========================
 Multicurrency revaluation
===========================

The *Multicurrency revaluation* module allows you generate automatically
multicurrency revaluation journal entries. You will also find here a
Revaluation report

Note that an extra aggregation by currency on general ledger & partner ledger
(from module : *account_financial_report*) has been added in order to get more
details.

---------------
 Main Features
---------------

* A checkbox *Allow currency revaluation* on accounts.
* A wizard to generate the revaluation journal entries. It adjusts account
balance having *Allow currency revaluation* checked.
* A wizard to print a report of revaluation.

The report uses webkit report system.

---------------
 Configuration
---------------

Due to the various legislation according the country, in the Company settings
you can set the way you want to generate revaluation journal entries.

Please, find below adviced account settings for 3 countries :

For UK (Revaluation)
====================
(l10n_uk Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [7700]  [7700]
  Provision B.S account  [    ]  [    ]
  Provision P&L account  [    ]  [    ]

For CH (Provision)
==================
(l10n_ch Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [    ]  [    ]
  Provision B.S account  [2331]  [2331]
  Provision P&L account  [3906]  [4906]

For FR
======
(l10n_fr Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [ 476]  [ 477]
  Provision B.S account  [1515]  [    ]
  Provision P&L account  [6865]  [    ]
""",

    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": 'AGPL-3',
    "depends": ["base",
                "account",
                "account_reversal",
                "base_headers_webkit"],
    "data": ["res_company_view.xml",
             "res_currency_view.xml",
             "security/security.xml",
             "account_view.xml",
             "wizard/wizard_currency_revaluation_view.xml",
             "wizard/print_currency_unrealized_report_view.xml",
             "report/report.xml"
             ],
    'installable': True,
 }
