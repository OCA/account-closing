# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _selection_closing_type(self):
        """Use selection values from move_type field in closing config
        (making a copy for preventing side effects), plus an extra value for
        non-closing moves."""
        res = list(
            self.env['account.fiscalyear.closing.config'].fields_get(
                allfields=['move_type']
            )['move_type']['selection']
        )
        res.append(('none', _('None')))
        return res

    fyc_id = fields.Many2one(
        comodel_name='account.fiscalyear.closing', delete="cascade",
        string="Fiscal year closing", readonly=True,
    )
    closing_type = fields.Selection(
        selection=_selection_closing_type, default="none",
        states={'posted': [('readonly', True)]},
    )

    @api.multi
    @api.depends('line_ids.debit', 'line_ids.credit')
    def _amount_compute(self):
        for move in self:
            this = move.with_context(search_fyc_moves=True)
            super(AccountMove, this)._amount_compute()
            move.amount = this.amount

    @api.model
    def search2(self, args, offset=0, limit=None, order=None, count=False):
        # Filter out moves from fiscal year closing unless they
        # were explicitly asked for
        if not self.env.context.get('search_fyc_moves', False):
            if args:
                if not any(item[0] == 'fyc_id' for item in args):
                    args.insert(0, ('fyc_id', '=', False))
            else:
                args = [('fyc_id', '=', False)]
        return super(AccountMove, self).search(
            args, offset=offset, limit=limit, order=order, count=count)
