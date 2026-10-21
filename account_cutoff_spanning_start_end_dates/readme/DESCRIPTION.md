This module allows to record the accruals whose period spans the cut-off
date on a different account than the other accruals.

For example, in Italy, at year end:

- a vendor bill dated after the cut-off date for an expense entirely
  before it is recorded on the account *Fatture da ricevere* (invoices
  to receive);
- a vendor bill dated after the cut-off date for an expense that spans
  the cut-off date is recorded on the account *Ratei passivi* (accrued
  expenses), for the part before the cut-off date.

The same applies to the revenue accruals (*Fatture da emettere* and
*Ratei attivi*).

The accrual lines generated from the start and end dates are marked as
*Spanning* when their end date is after the cut-off date. The journal
entry of the cut-off uses the *Cut-off Spanning Account* as counterpart
of these lines and of their taxes, and the *Cut-off Account* as
counterpart of the other lines.
