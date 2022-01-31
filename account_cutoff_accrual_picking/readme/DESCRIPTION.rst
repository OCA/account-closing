This module generates expense and revenue accruals based on the status of
orders, pickings and invoices.

To understand the behavior of this module, let's take the example of an expense accrual. When you click on the button *Re-Generate Lines* of an *Expense Accrual*:

1. Odoo will look for all incoming picking in Done state with a *Transfer Date* <= *Cut-off Date* (for performance reasons, by default, the incoming picking dated before *Cut-off Date* minus 90 days will not be taken into account (this limit is configurable via the field *Picking Analysis*). It will go to the stock moves of this picking and see if they are linked to a purchase order line.
2. Once this analysis is completed, Odoo has a list of purchase order lines to analyse for potential expense accrual.
3. For each of these purchase order lines, Odoo will:

   - scan the related stock moves in *done* state and check their transfer date,
   - scan the related invoices lines and check their invoice date.

4. If, for a particular purchase order line, the quantity of products shipped before the cutoff-date (or on the same day) minus the quantity of products invoiced before the cut-off date (or on the same day) is positive, Odoo will generate a cut-off line.

This module should work well with multiple units of measure (including products purchased and invoiced in different units of measure) and in multi-currency.
