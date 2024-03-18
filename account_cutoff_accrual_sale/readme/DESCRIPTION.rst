This module extends the functionality of account_cutoff_accrual_order_base
to allow the computation of revenue cutoffs on sales orders.

The accrual is computed by comparing on the order, the quantity
delivered/received and the quantity invoiced. In case, some deliveries or
invoices have occurred after the cutoff date, those quantities can be affected
and are recomputed. This allows to quickly generate a cutoff snapshot by
processing few lines.

For SO, you can make the difference between:
* invoice to generate (delivered qty > invoiced qty)
* goods to send (prepayment) (delivered qty < invoiced qty)

At each end of period, a cron job generates the cutoff entries for the revenues
(based on SO).

Orders forced in status invoiced won't have cutoff entries.

Once the cutoff lines have been generated but the accounting entries are not yet
created, you are still able to create or modify invoices before the accounting
butoff date. The cutoff lines will be adapted automatically to reflect the new
situation.

Once the cutoff accounting entries are generated you cannot create or modify
invoices before the accounting cutoff date.
