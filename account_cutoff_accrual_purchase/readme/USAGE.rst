To use this module, you need to:

#. Go to Accounting - Cut-offs to configure and generate the cutoffs

Examples
========

* Purchase Order with quantity received: 0, quantity invoiced: 0
  This will not make an cutoff entry

* Purchase Order with quantity received: 10, quantity invoiced: 0
  This will make an cutoff entry with invoice to receive: 10

* Purchase Order with quantity received: 0, quantity invoiced: 10
  This will make an cutoff entry with goods to receive: 10

* Purchase Order with quantity received: 10, quantity invoiced: 0
  This will make an cutoff entry with invoice to receive: 10
  Invoice is encoded after the cut-off date but dated before the cut-off date
  The cutoff entry is updated in the existing cut-off

* Purchase Order with quantity received: 0, quantity invoiced: 0
  This will not make an cutoff entry
  Invoice is encoded after the cut-off date but dated before the cut-off date
  An cutoff entry is added in the existing cut-off
