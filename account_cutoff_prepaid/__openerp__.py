# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
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
    'name': 'Account Cut-off Prepaid',
    'version': '0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Prepaid Expense, Prepaid Revenue',
    'description': """
Manage prepaid expense and revenue based on start and end dates
===============================================================

This module adds a **Start Date** and **End Date** field on invoice lines. For example, if you have an insurance contrat for your company that run from April 1st 2013 to March 31st 2014, you will enter these dates as start and end dates on the supplier invoice line. If your fiscal year ends on December 31st 2013, 3 months of expenses are part of the 2014 fiscal year and should not be part of the 2013 fiscal year. So, thanks to this module, you will create a *Prepaid Expense* on December 31st 2013 and OpenERP will identify this expense with the 3 months that are after the cut-off date and propose to generate the appropriate cut-off journal entry.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['account_cutoff_base'],
    'data': [
        'company_view.xml',
        'product_view.xml',
        'account_invoice_view.xml',
        'account_view.xml',
        'account_cutoff_view.xml',
    ],
    'demo': ['product_demo.xml'],
    'images': [
        'images/prepaid_revenue_draft.jpg',
        'images/prepaid_revenue_journal_entry.jpg',
        'images/prepaid_revenue_done.jpg',
        ],
    'installable': True,
    'active': False,
    'application': True,
}
