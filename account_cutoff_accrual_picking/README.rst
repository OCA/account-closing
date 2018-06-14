.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============================
Account cutoff accrual picking
==============================

This module extends the functionality of account_cutoff_accrual_base
to allow the calculation of expense and revenue accruals on sale order and
purchase order.
His name is a little misleading because following model changes in
v10 of Odoo it now bases its calculation not on stock picking anymore but
on sale and purchase order.

The calculation is done on purchase/order lines with a difference between
the quantity received/send and the quantity invoiced.

A cron job generates at each end of period cutoff entries for expenses (based
on PO) and revenues (based on SO). This is because we cannot identify in the
past, entries for which a cutoff must be generated. That cutoff entry store the
quantity received and invoiced at that date. Note that the invoiced quantity is
increased as soon as a draft invoice is created. We consider that the invoice
will be validated and the invoice accounting date will not change. If you
modify the quantity in an invoce or create a new invoice after the cutoff has
been generated, that cutoff will be updated when the invoice is validated. It is
also updated when the invoice is deleted. Nevertheless, this will be forbidden
if the accounting entry related to the cutoff is created.

Installation
============

This module is installed like any other module.

Configuration
=============

To configure this module, you need to:

#. Go to the accounting settings to select the journals and accounts used for
   the cutoff.
#. Analytic accounting needs to be enable in Accounting - Settings.
#. If you want to also accrue the taxes, you need in Accounting - Taxes, for
   each type of taxes an accrued tax account.

Usage
=====

To use this module, you need to:

#. Go to Accounting - Cut-offs to configure and generate the accruals

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/account-closing/10.0

Examples
========

* Purchase Order with quantity received: 0, quantity invoiced: 0
  This will not make an accrual entry

* Purchase Order with quantity received: 10, quantity invoiced: 0
  This will make an accrual entry with invoice to receive: 10

* Purchase Order with quantity received: 0, quantity invoiced: 10
  This will make an accrual entry with goods to receive: 10

* Purchase Order with quantity received: 10, quantity invoiced: 0
  This will make an accrual entry with invoice to receive: 10
  Invoice is encoded after the cut-off date but dated before the cut-off date
  The accrual entry is updated in the existing cut-off

* Purchase Order with quantity received: 0, quantity invoiced: 0
  This will not make an accrual entry
  Invoice is encoded after the cut-off date but dated before the cut-off date
  An accrual entry is added in the existing cut-off


Known issues / Roadmap
======================

* Although a cut-off date can be given for generating the accruals, it does not work correctly with the module as it is, and the calculation is done on the current date only.
  To workaround this issue, cron jobs generate the cutoff entries at end of period

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-closing/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

The module was developped by
* Alexis de Lattre from Akretion <alexis.delattre@akretion.com>
And migrated to Odoo v10 by
* Thierry Ducrest <thierry.ducrest@camptocamp.com>
* Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.

## Notes about migration to v.10
Historically, this module manages accrued expenses and revenues based on stock-picking.
But following changes up to v.10 in the odoo database schema it can not function as before.




