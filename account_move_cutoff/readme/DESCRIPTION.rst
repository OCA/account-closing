This module allows to generate cu-toff entries automatically when posting former
entries.

This module is based on `account_invoice_start_end_dates`
which allows to define start end end dates on invoice line (`account.move.line`).


Following assumption have been made before developing this module::

  - New method to compute cutoff amounts can be add by business modules


.. note::

    This module as been developed with some opinionated design
    do not depends on `account_cutoff_base`. Because::

      - we don't want rely on user nor async task at the end of
        each month (period)
      - link entries to understand the history without merging amounts
        in order to be able to keep details on deferred account
        move line (analytics, partners, accounts and so on)
