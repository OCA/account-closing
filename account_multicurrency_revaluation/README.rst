.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
Multicurrency revaluation
=========================

This module was written to extend the functionality of the accounting module to
support the multicurrency and to allow you to generate automatically
revaluation journal entries.

Installation
============

To install this module, you need to:

* clone the branch 9.0 of the repository https://github.com/OCA/account-closing
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Multicurrency revaluation" in your addons
* install the module

Configuration
=============

Due to the various legislation according the country, in the Accounting settings
you can set the way you want to generate revaluation journal entries.

The user that can access to the edition of the 'Provision B.S loss account' and
'Provision P&L accounts' need to be in the security group
'Additional provisioning entries posting'.

You also need to tick the box "Allow multi currencies" in the menu Settings/
Configuration/ Invoicing to be able to select the currency on the account you
want to revaluate.

Please, find below advised account settings for 3 countries:

For UK (Revaluation)
--------------------
(l10n_uk Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [7700]  [7700]
  Provision B.S account  [    ]  [    ]
  Provision P&L account  [    ]  [    ]

For CH (Provision)
------------------
(l10n_ch Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [    ]  [    ]
  Provision B.S account  [2331]  [2331]
  Provision P&L account  [3906]  [4906]

For FR
------
(l10n_fr Chart of account)

::

                          LOSS    GAIN
  Revaluation account    [ 476]  [ 477]
  Provision B.S account  [1515]  [    ]
  Provision P&L account  [6865]  [    ]

Usage
=====

To use this module, you need to:

* Check *Allow currency revaluation* on accounts you want to revaluate.
* Open the wizard 'Invoicing > Adviser > Currency Revaluation' to generate the
  revaluation journal entries. It adjusts account balance having
  *Allow currency revaluation* checked.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/89/9.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/account-closing/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Alexandre Fayolle
* Alexis de Lattre
* Frédéric Clementi
* Guewen Baconnier @ Camptocamp
* Joel Grand-Guillaume
* Kinner Vachhani
* Matt Choplin choplin.mat@gmail.com
* Matthieu Dietrich
* moylop260
* Pedro M. Baeza
* Stéphane Bidoul
* Vincent Renaville
* Yannick Vaucher
* Akim Juillerat


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
