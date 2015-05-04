.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Manage prepaid expense and revenue based on start and end dates
===============================================================

This module adds a **Start Date** and **End Date** field on invoice lines. For
example, if you have an insurance contrat for your company that run from April
1st 2013 to March 31st 2014, you will enter these dates as start and end dates
on the supplier invoice line. If your fiscal year ends on December 31st 2013,
3 months of expenses are part of the 2014 fiscal year and should not be part of
the 2013 fiscal year. So, thanks to this module, you will create a *Prepaid
Expense* on December 31st 2013 and OpenERP will identify this expense with the
3 months that are after the cut-off date and propose to generate the
appropriate cut-off journal entry.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com>
for any help or question about this module.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis@via.ecp.fr>
* Stéphane Bidoul <stephane.bidoul@acsone.eu>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
