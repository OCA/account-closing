# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, models


class CutoffPeriodMixin(models.AbstractModel):
    _name = "cutoff.period.mixin"
    _description = "Utilities method related to cuttoff mixins"

    @api.model
    def _first_day_of_month(self, date_):
        """Return the first day of the month for the given date or datetime
        returned as date
        """
        if isinstance(date_, datetime):
            date_ = date_.date()
        return date_ + relativedelta(day=1)

    @api.model
    def _period_from_date(self, date_):
        return self._first_day_of_month(date_)

    @api.model
    def _last_day_of_month(self, date_):
        """Return the last day of the month for the given date or datetime
        as date
        """
        # * add 1 month (datetime util return the last day of the next month
        #   in case date does not exists)
        # * get the first of the month
        # * then get the day before
        if isinstance(date_, datetime):
            date_ = date_.date()
        return date_ + relativedelta(months=1, day=1, days=-1)

    @api.model
    def _generate_monthly_periods(self, date_from, date_to):
        """Return a list of period. The first day of each month
        between date_from and date_to including the months of
        date_from and date_to.
        """
        periods = []
        current_period = self._period_from_date(date_from)
        while current_period <= date_to:
            periods.append(current_period)
            current_period += relativedelta(months=1)

        return periods

    def group_recordset_by(self, key):
        """Return a collection of pairs ``(key, recordset)`` from ``self``. The
        ``key`` is a function computing a key value for each element. This
        function is similar to ``itertools.groupby``, but aggregates all
        elements under the same key, not only consecutive elements.

        it's also similar to ``òdoo.tools.misc.groupby`` but return a recordset
        of account.move.line instead empty list

        this let write some code likes this::

            my_recordset.filtered(
                lambda record: record.to_use
            ).group_recordset_by(
                lambda record: record.type
            )

        # TODO: consider moving this method on odoo.models.Model
        """
        groups = defaultdict(self.env[self._name].browse)
        for elem in self:
            groups[key(elem)] |= elem
        return groups.items()
