This module allows you to easily compute the prepaid revenue/expenses
and also the revenue/expense accruals by using the **Start Date** and
**End Date** fields of invoice lines/journal items.

For example, if you have an insurance contrat invoiced in April 2020
that run from April 1st 2020 to March 31st 2021, you will enter these
dates as start and end dates on the supplier invoice line. If your
fiscal year ends on December 31st 2020, 3 months of expenses are part of
the 2021 fiscal year and should not be part of the 2020 fiscal year. So,
thanks to this module, you will create a *Prepaid Expense* on December
31st 2020 and Odoo will identify this expense with the 3 months that are
after the cut-off date and propose to generate the appropriate cut-off
journal entry.

Another example: you have a UPS invoice dated January 5th 2021 that
covers the shipments of December 2020. When you encode this vendor bill,
set the start date as December 1st 2020 and the end date as December
31st 2020. Then, thanks to this module, you will create an *Expense
Accrual* dated December 31st 2020 that will generate a cut-off journal
entry that will "move" the UPS expense from 2021 to 2020.

The **Calculation Method** field provides two options for prepaid and
accrued expenses and revenues:

- **Pending Amount** (default): compute the full cut-off amount at the
  closing date, preserving the existing behavior. Reverse the journal
  entry, automatically or manually, when required before the next closing.
- **Difference Since Last Cut-off**: compute the cumulative amount for
  each source journal item and subtract the amount stored in the previous
  posted cut-off of the same company and type. The first cut-off uses zero
  as the previous amount. Each new journal entry records only the variation,
  without reversing the previous entry.

For example, if a prepaid expense has a pending amount of 600 at the first
closing and 400 at the next one, the difference method records 600 followed
by -200. A final closing at the end of the service records -400, leaving
no deferred balance. For accruals, the remaining provision is released when
the closing date reaches the invoice accounting date. Accrual tax amounts
are also calculated by differences.

The difference method requires automatic reversal to be disabled and is
not available in forecast mode. Post each cut-off journal entry before
generating the next cut-off's lines. Switching from the default method is
allowed only if the previous posted cut-off has a posted reversal dated
on or before the new closing date; the new chain then starts from zero.
Dependent cut-offs must be reset to draft before resetting an earlier one.
