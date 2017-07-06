.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Multicurrency revaluation report
================================

This module was written to extend the functionality of the *Multicurrency
revaluation* module for additional reports.

Installation
============

To install this module, you need to:

* clone the branch 9.0 of the repository https://github.com/OCA/account-closing
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Multicurrency revaluation report" in your addons
* install the module

Configuration
=============

See the configuration in the module "Multicurrency revaluation"

Usage
=====

In the menu open the report through the following menu:

Accounting/Reporting/Legal Reports/Accounting Reports/Print Currency Unrealized

Main Features
-------------

* A wizard to print a report of revaluation.


Known issues / Roadmap
======================

* The module depends on the module *base headers webkit* which is in work in
  progress in this pull request: https://github.com/OCA/webkit-tools/pull/10

However, this PR has been blocked since September 2014 now by this issue:
https://github.com/odoo/odoo/issues/2334

And it is not sure if we are going to carry on with webkit or use the Qweb
reporting system now.


Credits
=======

Contributors
------------

* Alexandre Fayolle
* Alexis de Lattre
* Frédéric Clementi
* Guewen Baconnier @ Camptocamp
* Joel Grand-Guillaume
* Kinner Vachhani
* Matt Choplin
* Matthieu Dietrich
* moylop260
* Pedro M. Baeza
* Stéphane Bidoul
* Vincent Renaville
* Yannick Vaucher
* Akim Juillerat


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
