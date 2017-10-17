.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

=======================
Account Invoice Accrual
=======================

Many companies want to establish a complete accounting situation at the end of
each period. An important aspect of this process is to accrue invoices for
which the goods or services were received / delivered but for which the invoice
has not been received / sent.

Account Invoice Accrual lets you easily create these provisions entries
from draft invoices. It adds an accrual button on draft and pro-forma invoices which
generates the accrual move. When the invoice is validated, the accrual move is 
automatically reversed.

Configuration
=============

The default accrual accounts can be configured on the company form.
Expense and revenue account can be mapped to other accounts when doing
accruals using the the mapping framework provided by the account_cutoff_base
modules (Accounting > Configuration > Accounts > Cut-off account mappings.

Usage
=====

This module adds a new Accrual button draft and pro-forma invoices. This button
triggers a wizard where the user can chose the accrual date, period, journal and account.
When later validating the invoice, the accrual move is automatically reversed 
in the same period as the invoice.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/89/10.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-closing/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Laetitia Gangloff (ACSONE) <laetitia.gangloff@acsone.eu>
* Adrien Peiffer (ACSONE) <adrien.peiffer@acsone.eu>
* Stéphane Bidoul (ACSONE) <stephane.bidoul@acsone.eu>
* Cédric Pigeon (ACSONE) <cedric.pigeon@acsone.eu>

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
