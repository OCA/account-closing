# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, exceptions, fields, models, _


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def move_line_get_item(self, line):
        res = super(AccountInvoiceLine, self)\
            .move_line_get_item(line,)
        if self.env.context.get('move_accrual') and self.env.context.get(
                'type'):
            mapping_obj = self.env['account.cutoff.mapping']
            if self.env.context.get('type', False) in ['out_invoice',
                                                       'out_refund']:
                mapping_type = 'accrued_revenue'
            else:
                mapping_type = 'accrued_expense'
            mapping = mapping_obj.\
                _get_mapping_dict(line.invoice_id.company_id.id,
                                  mapping_type)
            res['account_id'] = mapping.get(line.account_id.id,
                                            line.account_id.id)
        return res


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    accrual_move_id = fields.Many2one(
        'account.move', 'Accrual Journal Entry',
        readonly=True, ondelete='set null', copy=False,
        help="Link to the Accrual Journal Items.")
    to_be_reversed = fields.Boolean(
        'To be reversed', related='accrual_move_id.to_be_reversed')

    def reverse_accruals(self):
        for invoice in self:
            if not invoice.to_be_reversed:
                continue
            accrual_move = invoice.accrual_move_id
            accrual_date = fields.Date.from_string(accrual_move.date)
            date = self.date or self.date_invoice
            invoice_date = fields.Date.from_string(date)

            if (accrual_move.state == 'draft' and
                    accrual_date.year == invoice_date.year and
                    accrual_date.month == invoice_date.month):
                # reversal in same month as accrual
                # and accrual move is still draft:
                # we simply remove it
                accrual_move.unlink()
            else:
                # Use default values of the reversal wizard to create the
                # reverse
                reverse_obj = self.env['account.move.reverse'].with_context(
                    active_id=accrual_move.id, active_ids=accrual_move.ids)
                reverse_wizard = reverse_obj.create({'date': invoice_date})
                reverse_wizard.action_reverse()

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.reverse_accruals()
        return res

    @api.multi
    def action_cancel(self):
        # See account_invoice_merge module
        if 'is_merge' not in self.env.context:
            for invoice in self:
                if invoice.to_be_reversed:
                    raise exceptions.Warning(
                        _('Please reverse accrual before cancelling invoice'))
        return super(AccountInvoice, self).action_cancel()

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.to_be_reversed:
                raise exceptions.Warning(
                    _('Please reverse accrual before deleting invoice'))
        return super(AccountInvoice, self).unlink()

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        date = self.env.context.get('accrual_date')
        for al in res.get('analytic_line_ids', []):
            # al : (0, 0, {vals})
            if not al[2].get('date', False) and date:
                al[2]['date'] = date
        return res

    @api.multi
    def _move_accrual(self, accrual_date, account_id,
                      accrual_journal_id=False, move_prefix=False,
                      move_line_prefix=False):
        """
        Create the accrual of a move

        :param invoice: browse instance of the invoice to accrue
        :param accrual_date: when the accrual must be input
        :param accrual_journal_id: facultative journal on which create
                                    the move
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names

        :return: Returns the id of the created accrual move
        """
        self.ensure_one()
        move_obj = self.env['account.move']

        company_currency = self.company_id.currency_id
        accrual_taxes = self.company_id.accrual_taxes
        taxes_fields = ['tax_ids', 'tax_line_id']

        if not accrual_journal_id:
            accrual_journal_id = self.journal_id.id

        accrual_ref = ''.join(
            [x for x in [move_prefix, self.reference and
                         self.reference or self.name, ] if x])

        iml = self.invoice_line_move_line_get()

        if not accrual_taxes:
            for line in iml:
                for field in taxes_fields:
                    if line.get(field, False):
                        line.pop(field)
        # check if taxes are all computed
        self.compute_taxes()

        # one move line per tax line
        if accrual_taxes:
            iml += self.tax_line_move_line_get()

        diff_currency_p = self.currency_id.id != company_currency.id
        # create one move line for the total and possibly adjust the other
        # lines amount
        total, total_currency, iml = self.compute_invoice_totals(
            company_currency, iml)
        if self.origin:
            name = self.origin
        else:
            name = '/'
        totlines = False
        if self.payment_term_id:
            totlines = self.payment_term_id.compute(total,
                                                    self.date_invoice or False)
        if totlines:
            totlines = totlines[0]
            res_amount_currency = total_currency
            i = 0
            for t in totlines:
                if self.currency_id.id != company_currency.id:
                    amount_currency = company_currency.with_context(
                        date=self.date_invoice).compute(
                        t[1], self.currency_id)
                else:
                    amount_currency = False

                # last line add the diff
                res_amount_currency -= amount_currency or 0
                i += 1
                if i == len(totlines):
                    amount_currency += res_amount_currency

                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': t[1],
                    'account_id': account_id,
                    'date_maturity': t[0],
                    'amount_currency': diff_currency_p and
                    amount_currency or False,
                    'currency_id': diff_currency_p and
                    self.currency_id.id or False,
                    'ref': accrual_ref,
                })
        else:
            iml.append({
                'type': 'dest',
                'name': name,
                'price': total,
                'account_id': account_id,
                'date_maturity': self.date_due or False,
                'amount_currency': diff_currency_p and total_currency or False,
                'currency_id': diff_currency_p and self.currency_id.id or
                False,
                'ref': accrual_ref
            })

        part = self.env['res.partner']._find_accounting_partner(
            self.partner_id)
        line = []
        for x in iml:
            vals = self.with_context(accrual_date=accrual_date)\
                .line_get_convert(x, part.id)
            line.append((0, 0, vals))
        line = self.group_lines(iml, line)
        line = self.finalize_invoice_move_lines(line)

        if move_line_prefix:
            # update all move name with prefix
            for ml in line:
                ml[2]['name'] = ' '.join(
                    [x for x in [move_line_prefix, ml[2]['name']] if x])

        move = {
            'ref': accrual_ref,
            'line_ids': line,
            'journal_id': accrual_journal_id,
            'date': accrual_date,
            'narration': self.comment,
            'company_id': self.company_id.id,
            'to_be_reversed': True,
        }

        accrual_move_id = move_obj.with_context(
            date=self.date_invoice, invoice=self).\
            create(move)
        # make the invoice point to that move
        self.with_context(
            date=self.date_invoice, invoice=self).\
            write({'accrual_move_id': accrual_move_id.id})
        self._post_accrual_move(accrual_move_id)

        return accrual_move_id.id

    @api.multi
    def _post_accrual_move(self, accrual_move_id):
        self.ensure_one()
        # Prevent passing invoice in context in method post: otherwise accrual
        # sequence could be the one from this invoice
        accrual_move_id.with_context(invoice=False).post()

    @api.multi
    def create_accruals(self, accrual_date, account_id,
                        accrual_journal_id=False,
                        move_prefix=False, move_line_prefix=False):
        """
        Create the accrual of one or multiple invoices

        :param accrual_date: when the accrual must be input
        :param accrual_journal_id: facultative journal on which create
                                    the move
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names

        :return: Returns a list of ids of the created accrual moves
        """

        accrued_move_ids = []
        for invoice in self:
            if invoice.state not in ('draft', 'proforma2'):
                continue  # skip the accrual creation if state is not draft

            accrual_move_id = invoice._move_accrual(
                accrual_date,
                account_id,
                accrual_journal_id=accrual_journal_id,
                move_prefix=move_prefix,
                move_line_prefix=move_line_prefix)

            if accrual_move_id:
                accrued_move_ids.append(accrual_move_id)

        return accrued_move_ids

    @api.multi  # because api.one wraps the result dict in a list
    def button_reversal(self):
        self.ensure_one()
        if not self.to_be_reversed:
            return False
        action = self.env.ref('account_reversal.act_account_move_reverse')
        date = self.date or self.date_invoice
        return {
            'type': action.type,
            'name': action.name,
            'res_model': action.res_model,
            'view_type': action.view_type,
            'view_mode': 'form',
            'view_id': action.view_id.id,
            'target': action.target,
            'context': {
                'active_model': 'account.move',
                'active_id': self.accrual_move_id.id,
                'active_ids': [self.accrual_move_id.id],
                'default_date': date,
            }
        }
