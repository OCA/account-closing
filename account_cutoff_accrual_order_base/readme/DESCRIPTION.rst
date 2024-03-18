This module extends the functionality of account_cutoff_base
to allow the computation of expense and revenue cutoffs on orders.

The accrual is computed by comparing on the order, the quantity
delivered/received and the quantity invoiced. In case, some deliveries or
invoices have occurred after the cutoff date, those quantities can be affected
and are recomputed. This allows to quickly generate a cutoff snapshot by
processing few lines.

You can configure to disable the generation of cutoff entries on orders.
For instance, if you know you will never receive the missing invoiced goods,
you can disable cutoff entries on a purchase order.

Once the cutoff lines have been generated but the accounting entries are not yet
created, you are still able to create or modify invoices before the accounting
butoff date. The cutoff lines will be adapted automatically to reflect the new
situation.

Once the cutoff accounting entries are generated you cannot create or modify
invoices before the accounting cutoff date.
Nevertheless, you can still reset to draft a supplier invoice but you won't be
able to modify any amount. You are then supposed to re-validate the invoice.

Warning: This module is replacing account_cutoff_picking and is incompatible with it.
