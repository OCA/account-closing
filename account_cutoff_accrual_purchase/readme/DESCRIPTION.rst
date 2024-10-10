This module extends the functionality of account_cutoff_accrual_order_base
to allow the computation of expense cutoffs on purchase orders.

The accrual is computed by comparing on the order, the quantity
delivered/received and the quantity invoiced. In case, some deliveries or
invoices have occurred after the cutoff date, those quantities can be affected
and are recomputed. This allows to quickly generate a cutoff snapshot by
processing few lines.

For PO, you can make the difference between:
* invoice to receive (received qty > invoiced qty)
* goods to receive (prepayment) (received qty < invoiced qty)

If you expect a refund, you can make it in draft. In standard, this update
the PO and the quantity will not be accrued as goods to receive. You can accrue
the draft credit note as "credit notes to receive".

Orders forced in status invoiced won't have cutoff entries.
For instance, if you know you will never receive the missing invoiced goods,
you can force it as invoiced.

Once the cutoff lines have been generated but the accounting entries are not yet
created, you are still able to create or modify invoices before the accounting
butoff date. The cutoff lines will be adapted automatically to reflect the new
situation.

Once the cutoff accounting entries are generated you cannot create or modify
invoices before the accounting cutoff date.
Nevertheless, you can still reset to draft a supplier invoice but you won't be
able to modify any amount. You are then supposed to re-validate the invoice.
