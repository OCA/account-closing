To compute the accrued revenue, go to the menu *Invoicing > Cut-offs
> Accrued Revenue* and click on the *Create* button. Enter the cut-off
date, check that the source journals contains all your sale journals
and click on the button *Re-Generate lines*: Odoo will scan all the
journal entries of the source journals and will get all the lines that
have a start date before or equal to the cut-off date and, for each line, it will
compute the revenue to provision. If you agree with the result, click on the
button *Create Journal Entry*: Odoo will generate an account move at the
cut-off date to provision these revenue. Hint: you can then use the reversal
feature to generate the reverse journal items on the next day.
