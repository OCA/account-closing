This module adds two company options, in the *Vendor Bills* and *Customer
Invoices* sections of the settings, to use the invoice date as default
Start Date and End Date of the lines of vendor bills and of customer
invoices.

The lines without dates are ignored by the cut-offs based on start/end
dates: with these options, the product lines that have no dates get the
invoice date as soon as it is set, so that the dates only have to be
entered on the lines that refer to another period. The dates already set
on a line are never overwritten.

The dates refer to the period of the invoice/move: when an invoice/move
is duplicated, the lines of the copy don't get the dates of the original
lines. The lines of a credit note keep the dates of the reversed invoice.
