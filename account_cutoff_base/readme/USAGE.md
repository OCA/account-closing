This module is used as a base for other cut-off modules. Please refer to
the README of the other cut-off modules.

Several cut-offs of the same type can have the same cut-off date only if
they don't include the same lines. Each module that generates cut-off
lines must extend the method `_is_cutoff_overlapping` to tell when its
lines would be included in both cut-offs.
