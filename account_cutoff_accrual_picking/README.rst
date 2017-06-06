.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================
Account Accrual Picking
=======================

This module generates expense and revenue accruals based on the status of
pickings.

For revenue accruals, Odoo will take into account all the delivery orders
in *Delivered* state that have been shipped before the cut-off date
with *Invoice Control* = *Invoiced*
with an invoice date after the cut-off date
or *Invoice Control* = *To Be Invoiced*.

For expense accruals, OpenERP will take into account all the incoming
shipments in *Received* state that have been received before the cut-off date
with *Invoice Control* = *Invoiced*
with an invoice date after the cut-off date
or *Invoice Control* = *To Be Invoiced*.

The current code of the module only works when:

* on sale orders, the *Create Invoice* field is set to *On Delivery Order*
* for purchase orders, the *Invoicing Control* field is set to *Based on incoming shipments*.

Installation
============

To install this module, you need to:

#. clone the branch 8.0 of the repository https://github.com/OCA/account-closing
#. add the path to this repository in your configuration (addons-path)
#. update the module list
#. search for "Account Accrual Picking" in your addons
#. install the module

Usage
=====

To use this module, you need to:

#. Go to ...

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/89/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-closing/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

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