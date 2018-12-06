This module adds the fields *Start Date* and *End Date* on invoice lines. When you validate the invoice, the information is copied from invoice lines to account move lines (if you enabled the grouping option on the related journal, Odoo will not group invoice lines that have different start/end dates).

It also adds an option *Must Have Start and End Dates* on the product form (in the *Accounting* tab) ; if you enable this option, you will get an error message if you try to validate an invoice that constains such a product on one of its lines and doesn't have start/end dates on that line.

If you use this module, you may also be interested in 2 other modules:

* the module *sale_start_end_dates* from the sale-workflow OCA project: this module adds the fields *Start Date* and *End Date* on sale order lines and copies the information from sale order lines to invoice lines.

* the module *account_cutoff_prepaid* (same repository): this module allows easy computation of prepaid expenses and prepaid revenues.
