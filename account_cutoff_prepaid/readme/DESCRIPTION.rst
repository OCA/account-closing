This module allows you to easily compute the prepaid revenue and prepaid expenses and to generate the related cutoff journal items. It uses the **Start Date** and **End Date** fields of journal entries (copied from the same fields of invoice lines).

For
example, if you have an insurance contrat for your company that run from April
1st 2013 to March 31st 2014, you will enter these dates as start and end dates
on the supplier invoice line. If your fiscal year ends on December 31st 2013,
3 months of expenses are part of the 2014 fiscal year and should not be part of
the 2013 fiscal year. So, thanks to this module, you will create a *Prepaid
Expense* on December 31st 2013 and OpenERP will identify this expense with the
3 months that are after the cut-off date and propose to generate the
appropriate cut-off journal entry.
