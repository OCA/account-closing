This module adds the fields *Start Date* and *End Date* on invoice/move lines.

It also adds an option *Must Have Start/End Dates* on the product form (in the *Accounting* tab) ; if you enable this option, you will get an error message if you try to post an invoice/move that constains such a product on one of its lines and doesn't have start/end dates on that line.

If you use this module, you may also be interested in several other modules:

* the module *sale_start_end_dates* from the `sale-workflow OCA project <https://github.com/OCA/sale-workflow>`_: this module adds the fields *Start Date* and *End Date* on sale order lines and copies the information from sale order lines to invoice/move lines.

* the modules *account_cutoff_prepaid* and *account_cutoff_accrual_dates* in the `account-closing OCA projct <https://github.com/OCA/account-closing>`_: these modules allow easy computation of prepaid expenses, prepaid revenues, accrued expense and accrued revenue using start/end dates.
