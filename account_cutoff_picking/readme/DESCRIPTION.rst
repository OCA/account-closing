This module extends the functionality of account_cutoff_cutoff_base
to allow the calculation of expense and revenue cutoffs on sale order and
purchase order.
His name is a little misleading because following model changes in
v10 of Odoo it now bases its calculation not on stock picking anymore but
on sale and purchase order.

The calculation is done on purchase/order lines with a difference between
the quantity received/send and the quantity invoiced.

A cron job generates at each end of period cutoff entries for expenses (based
on PO) and revenues (based on SO). This is because we cannot identify in the
past, entries for which a cutoff must be generated. That cutoff entry store the
quantity received and invoiced at that date. Note that the invoiced quantity is
increased as soon as a draft invoice is created. We consider that the invoice
will be validated and the invoice accounting date will not change. If you
modify the quantity in an invoce or create a new invoice after the cutoff has
been generated, that cutoff will be updated when the invoice is validated. It is
also updated when the invoice is deleted. Nevertheless, this will be forbidden
if the accounting entry related to the cutoff is created.
