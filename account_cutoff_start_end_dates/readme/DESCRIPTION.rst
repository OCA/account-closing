This module allows you to easily compute the prepaid revenue/expenses and also the revenue/expense accruals by using the **Start Date** and **End Date** fields of invoice lines/journal items.

For example, if you have an insurance contrat invoiced in April 2020 that run from April
1st 2020 to March 31st 2021, you will enter these dates as start and end dates
on the supplier invoice line. If your fiscal year ends on December 31st 2020,
3 months of expenses are part of the 2021 fiscal year and should not be part of
the 2020 fiscal year. So, thanks to this module, you will create a *Prepaid
Expense* on December 31st 2020 and Odoo will identify this expense with the
3 months that are after the cut-off date and propose to generate the
appropriate cut-off journal entry.

Another example: you have a UPS invoice dated January 5th 2021 that covers the shipments of December 2020. When you encode this vendor bill, set the start date as December 1st 2020 and the end date as December 31st 2020. Then, thanks to this module, you will create an *Expense Accrual* dated December 31st 2020 that will generate a cut-off journal entry that will "move" the UPS expense from 2021 to 2020.
