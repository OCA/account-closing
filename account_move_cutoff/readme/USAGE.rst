
To handle deferred accounting, follow these steps:

1. Set the start and end date, where the end date is at least set to
   the month after the current entry posted date.

2. Ensure that the account (the `account.account` configuration)
   in use is linked to a deferred account.

3. Post the entry.

4. After posting, check deferred entries have been generated, posted, and
   reconciled if needed.

.. note::

   This module only defers amounts in periods subsequent to the accounting period
   date. For example, if an invoice is posted on March 2nd for a service from
   January 1st to March 31st at 1000€ per month, the deferred amount will be
   only 1000€ for March, leaving 2000€ in February. We never add accounting items
   in periods previous to the current entry date.
