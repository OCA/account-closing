Deferred journal(s)
~~~~~~~~~~~~~~~~~~~

In accounting configuration you should set
Deferred Revenue and Expense journal to be used
on generated entries.

.. note::

    Journal will be used according the kind of
    journal used by the former entry: `sale` or `purchase`


Deferred account(s)
~~~~~~~~~~~~~~~~~~~

On each Revenue/Expense account you can set the deferred
Revenue/Expense account.

Only invoice lines linked to account with a deferred account set
will generate deferred Revenue/Expense.


Cut-off Method
~~~~~~~~~~~~~~

In the first version of this module, two cut-off computation methods are
supported and can be configured using the ``account_move_cutoff.default_cutoff_method``
key. The currently possible values are ``monthly_prorata_temporis`` or ``equal``.

Before defining these values, let's provide some context by using an example to
illustrate the definitions. Consider a sales invoice that is posted on January
16th for a service that spans from the 8th of January to the 15th of March. So, there are
24 days in January, 1 full month in February, and 15 days in March. The product
is sold for 1000 for a month, so the invoice line amount (excluding VAT) is
calculated as follows::

    24/31 * 1000 + 1000 + 15/31 * 1000 = 2258.06

* **monthly_prorata_temporis** (the default if not set): This method splits amounts
  over the rate of the month the product has been used. The results would be as
  follows:

  - January: **774.19** (`2258.06 - 1000 - 483.87`) (Subtraction is used here to avoid
    rounding discrepancies.)
  - February: **1000.00** (`1 * 2258.06 / (24/31 + 1 + 15/31)`)
  - March: **483.87** (`15/31 * 2258.06 / (24/31 + 1 + 15/31)`)

* **equal**: With this method, the same amount is split over the months of service.

  - January: **752.68** (`2258.06 - 752.69 - 752.69`)
  - February: **752.69** (2258.06 / 3)
  - March: **752.69** (2258.06 / 3)

Please note that this information is subject to change based on updates to the
module. Always refer to the latest documentation for accurate details.
