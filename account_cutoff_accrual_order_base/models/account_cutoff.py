# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from datetime import datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import split_every

_logger = logging.getLogger(__name__)


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    order_line_model = fields.Selection(
        selection=[],
        readonly=True,
    )

    def _nextday_start_dt(self):
        """Convert the cutoff date into datetime as start of next day."""
        next_day = self.cutoff_date + timedelta(days=1)
        tz = self.env.company.partner_id.tz or "UTC"
        start_next_day = datetime.combine(
            next_day, time(0, 0, 0, 0, tzinfo=pytz.timezone(tz))
        )
        return start_next_day.replace(tzinfo=None)

    def _get_product_account(self, product, fpos):
        if self.cutoff_type in "accrued_revenue":
            map_type = "income"
        elif self.cutoff_type in "accrued_expense":
            map_type = "expense"
        else:
            return
        account = product.product_tmpl_id.get_product_accounts(fpos)[map_type]
        if not account:
            raise UserError(
                _(
                    "Error: Missing {map_type} account on product '{product}' or on"
                    " related product category.",
                ).format(
                    map_type=map_type,
                    product=product.name,
                )
            )
        return account

    def get_lines(self):
        self.ensure_one()
        # If the computation of the cutoff is done at the cutoff date, then we
        # only need to retrieve lines where there is a qty to invoice (i.e.
        # delivered qty != invoiced qty).
        # For any line where a move or an invoice has been done after the
        # cutoff date, we need to recompute the quantities.
        res = super().get_lines()
        if not self.order_line_model:
            return res

        model = self.env[self.order_line_model]
        _logger.debug("Get model lines")
        line_ids = set(model.browse(model._get_cutoff_accrual_lines_query(self)).ids)
        _logger.debug("Get model lines invoiced after")
        line_ids |= set(model._get_cutoff_accrual_lines_invoiced_after(self).ids)
        _logger.debug("Get model lines delivered after")
        line_ids |= set(model._get_cutoff_accrual_lines_delivered_after(self).ids)

        _logger.debug("Prepare cutoff lines per chunks")
        # A good chunk size is per 1000. If bigger, it is not faster but memory
        # usage increases. If too low, then it takes more cpu time.
        for chunk in split_every(models.INSERT_BATCH_SIZE * 10, tuple(line_ids)):
            lines = model.browse(chunk)
            values = []
            for line in lines:
                data = line._prepare_cutoff_accrual_line(self)
                if not data:
                    continue
                values.append(data)
            self.env["account.cutoff.line"].create(values)
            # free memory usage
            self.env.invalidate_all()
            _logger.debug("Prepare cutoff lines - next chunk")
        return res

    @api.model
    def _cron_cutoff(self, cutoff_type, model):
        # Cron is expected to run at begin of new period. We need the last day
        # of previous month. Support some time difference and compute last day
        # of previous period.
        last_day = datetime.today()
        if last_day.day > 20:
            last_day += relativedelta(months=1)
        last_day = last_day.replace(day=1)
        last_day -= relativedelta(days=1)
        cutoff = self.with_context(default_cutoff_type=cutoff_type).create(
            {
                "cutoff_date": last_day,
                "cutoff_type": cutoff_type,
                "order_line_model": model,
                "auto_reverse": True,
            }
        )
        cutoff.get_lines()
