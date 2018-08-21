# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.translate import _


class AccountMoveAccrual(models.TransientModel):
    _name = "account.move.accrue"
    _description = "Create accrual of draft invoices"

    date = fields.Date(
        'Accrual Date',
        required=True,
        default=lambda x: x._default_date(),
        help="Enter the date of the accrual account entries. "
             "By default, Odoo proposes the last day of "
             "the previous month.")
    account_id = fields.Many2one(
        'account.account',
        'Accrual account',
        default=lambda x: x._default_account(),
        required=True,)
    journal_id = fields.Many2one(
        'account.journal',
        'Accrual Journal',
        default=lambda x: x._default_journal(),
        help='')
    move_prefix = fields.Char(
        'Entries Ref. Prefix',
        size=32,
        help="Prefix that will be added to the 'Ref' of the journal "
             "entry to create the 'Ref' of the "
             "accrual journal entry (no space added after the prefix).")
    move_line_prefix = fields.Char(
        'Items Name Prefix',
        size=32,
        default="ACC -",
        help="Prefix that will be added to the name of the journal "
             "item to create the name of the accrual "
             "journal item (a space is added after the prefix).")

    @api.model
    def _default_date(self):
        return fields.Date.today()

    @api.model
    def _default_journal(self):
        journal_id = False
        if self.env.context.get('active_model') and self.env.context.get(
                'active_ids') \
                and self.env.context['active_model'] == 'account.invoice':
            inv = self.env['account.invoice'].browse(
                self.env.context['active_ids'])[0]
            if inv.type in ('out_invoice', 'out_refund'):
                journal_id = \
                    inv.company_id.default_accrual_revenue_journal_id.id or\
                    inv.company_id.default_cutoff_journal_id.id
            else:
                journal_id =\
                    inv.company_id.default_accrual_expense_journal_id.id or\
                    inv.company_id.default_cutoff_journal_id.id
        return journal_id

    @api.model
    def _default_account(self):
        account = False
        if self.env.context.get('active_model') and self.env.context.get(
                'active_ids') \
                and self.env.context['active_model'] == 'account.invoice':
            inv = self.env['account.invoice'].browse(
                self.env.context['active_ids'])[0]
            if inv.type == 'out_invoice':
                account = inv.company_id.default_accrued_revenue_account_id
            elif inv.type == 'out_refund':
                account = inv.company_id\
                    .default_accrued_revenue_return_account_id or\
                    inv.company_id.default_accrued_revenue_account_id
            elif inv.type == 'in_invoice':
                account = inv.company_id.default_accrued_expense_account_id
            elif inv.type == 'in_refund':
                account = inv.company_id\
                    .default_accrued_expense_return_account_id or\
                    inv.company_id.default_accrued_expense_account_id
        return account

    @api.multi
    def action_accrue(self):
        self.ensure_one()
        assert 'active_ids' in self.env.context,\
            "active_ids missing in context"

        inv_ids = self.env.context['active_ids']
        invoices = self.env['account.invoice'].browse(inv_ids)

        journal_id = self.journal_id.id or False

        accrual_move_ids = invoices.create_accruals(
            self.date,
            self.account_id.id,
            accrual_journal_id=journal_id,
            move_prefix=self.move_prefix,
            move_line_prefix=self.move_line_prefix)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accrual Entries'),
            'res_model': 'account.move',
            'domain': [('id', 'in', accrual_move_ids)],
            "views": [[False, "tree"], [False, "form"]],
        }
