To compute the prepaid revenue, go to the menu *Accounting > Cut-offs
> Prepaid Revenue* and click on the *Create* button. Enter the cut-off
date, check that the source journals contains all your sale journals
and click on the button *Re-Generate lines*: Odoo will scan all the
journal entries of the source journals and will get all the lines that
have an end date after the cut-off date and, for each line, it will
compute the prepaid revenue. If you agree with the result, click on the
button *Create Journal Entry*: Odoo will generate an account move at the
cut-off date to cut these prepaid revenue. Hint: you can then use the reversal
feature to generate the reverse journal entry on the next day.

If you need to answer a question such as *How much revenue did I already
invoice for my next fiscal year ?*, you will be interested by the
*forecast* feature. For that, on the Prepaid Revenue form, click on
the *Forecast* option and you will see 2 new fields: *Start Date* and
*End Date*. Enter the start date and the end date of your next fiscal
year and click on the button *Re-Generate lines*: you will see all the
revenue that you already have in your source journals for that period.
