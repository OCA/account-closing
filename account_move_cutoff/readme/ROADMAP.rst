- Make the is_deferrable_line a storable field to allow end user to not
  deferred a given line while posting entry. (but should raise if
  it's not possible to force the value to true)
- allow to change/configure cutoff frequency (weekly/monthly/...)
  today only monthly is implemented
- allow to configure cutoff computation method in different
  place (product / invoice lines /...)
