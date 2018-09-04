.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============================
Account Cut-off Accrual Picking
===============================

This module generates expense and revenue accruals based on the status of
orders, pickings and invoices.

To understand the behavior of this module, let's take the example of an expense accrual. When you click on the button *Re-Generate Lines* of an *Expense Accrual*:

1. Odoo will look for all incoming picking in Done state with a *Transfer Date* <= *Cut-off Date* (for performance reasons, by default, the incoming picking dated before *Cut-off Date* minus 3 months will not be taken into account (this limit can be easily changed via a method inheritance). It will go to the stock moves of this picking and see if they are linked to a purchase order line.
2. Once this analysis is completed, Odoo has a list of purchase order lines to analyse for potential expense accrual.
3. For each of these purchase order lines, Odoo will:

  - scan the related stock moves in *done* state and check their transfer date,
  - scan the related invoices lines in *open* or *paid* state and check their invoice date.

4. if, for a particular purchase order line, the quantity of products shipped before the cutoff-date (or on the same day) minus the quantity of products invoiced before the cut-off date (or on the same day) is positive, Odoo will generate a cut-off line.

This module should work well with multiple units of measure (including products purchased and invoiced in different units of measure) and in multi-currency.

Configuration
=============

For configuration instructions, refer to the README of the modules *account_cutoff_base* and *account_cutoff_accrual_base*.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/89/10.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-closing/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

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
