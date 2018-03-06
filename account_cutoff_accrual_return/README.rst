.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============================
Account cutoff accrual returns
==============================

This module extends the functionality of account_cutoff_accrual_picking
to allow the calculation of expense and revenue accruals on returned goods to supplier or from customer.

The computation is done based on stock inventory on return locations marked as
to be accrued.

Installation
============

This module is installed like any other module.

Configuration
=============

To configure this module, you need to:

#. Go to the setting page of the company on the cutoff tab to select the
   accounts used for the calculation.
#. Go to your return locations and mark then as to be accrued.

Usage
=====

To use this module, you need to:

#. Go to Accounting - Cut-offs to configure and generate the accruals

Known issues / Roadmap
======================

* Although a cut-off date can be given for generating the accruals, it does not work correctly with the module as it is, and the calculation is done on the current date only.

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
