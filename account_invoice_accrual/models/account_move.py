# Copyright 2017 ACSONE SA/NV
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, exceptions, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    accrual_move_id = fields.Many2one(
        "account.move",
        "Accrual Journal Entry",
        readonly=True,
        ondelete="set null",
        copy=False,
        help="Link to the Accrual Journal Items.",
    )
    to_be_reversed = fields.Boolean("To be reversed")
    accrual_move_to_be_reversed = fields.Boolean(
        related="accrual_move_id.to_be_reversed", string="accrual move to be reversed"
    )

    def reverse_accruals(self):
        for move in self:
            if not move.is_invoice() or not move.accrual_move_to_be_reversed:
                continue
            accrual_move = move.accrual_move_id
            accrual_date = accrual_move.date
            invoice_date = self.date or self.invoice_date
            if (
                accrual_move.state == "draft"
                and accrual_date.year == invoice_date.year
                and accrual_date.month == invoice_date.month
            ):
                # reversal in same month as accrual
                # and accrual move is still draft:
                # we simply remove it
                accrual_move.unlink()
            else:
                # Use default values of the reversal wizard to create the
                # reverse
                move_reversal = (
                    self.env["account.move.reversal"]
                    .with_context(
                        active_model="account.move", active_ids=accrual_move.ids
                    )
                    .create(
                        {
                            "date": invoice_date,
                            "refund_method": "cancel",
                            "journal_id": accrual_move.journal_id.id,
                        }
                    )
                )
                move_reversal.reverse_moves()

    def action_post(self):
        res = super().action_post()
        self.reverse_accruals()
        return res

    def button_cancel(self):
        for move in self:
            if move.accrual_move_to_be_reversed:
                raise exceptions.Warning(
                    _("Please reverse accrual before cancelling invoice")
                )
        return super().button_cancel()

    def unlink(self):
        for move in self:
            if move.accrual_move_to_be_reversed:
                raise exceptions.Warning(
                    _("Please reverse accrual before deleting invoice")
                )
        return super().unlink()

    def _get_accrual_move_line_vals(
        self, name, balance, account, date_maturity, accrual_ref
    ):
        return {
            "name": name,
            "debit": balance > 0 and balance,
            "credit": balance < 0 and -balance,
            "account_id": account.id,
            "date_maturity": date_maturity,
            "amount_currency": balance,
            "currency_id": self.currency_id.id,
            "ref": accrual_ref,
        }

    def _get_accrual_move_line_name(self, move_line_prefix):
        if self.invoice_origin:
            name = self.invoice_origin
        else:
            name = "/"
        if move_line_prefix:
            name = " ".join([move_line_prefix, name])
        return name

    def _get_accrual_move_lines_vals(self, account, move_prefix, move_line_prefix):
        accrual_ref = self._get_accrual_ref(move_prefix)
        name = self._get_accrual_move_line_name(move_line_prefix)
        res = []
        if self.invoice_payment_term_id:
            for term_line in self.invoice_payment_term_id._compute_terms(
                self.invoice_date or False,
                self.currency_id,
                self.company_id,
                0,
                0,
                self.amount_untaxed / self.amount_untaxed_signed,
                self.amount_untaxed,
                self.amount_untaxed,
            ):
                balance = term_line.get("company_amount")
                date_maturity = term_line.get("date")
                res.append(
                    self._get_accrual_move_line_vals(
                        name, balance, account, date_maturity, accrual_ref
                    )
                )
        else:
            balance = self.amount_untaxed_signed
            date_maturity = self.date or self.invoice_date
            res.append(
                self._get_accrual_move_line_vals(
                    name, balance, account, date_maturity, accrual_ref
                )
            )
        return res

    def _get_accrual_ref(self, move_prefix):
        return "".join(
            [x for x in [move_prefix, self.ref and self.ref or self.name] if x]
        )

    def _get_accrual_move_vals(
        self,
        accrual_date,
        account,
        accrual_journal_id,
        move_prefix,
        move_line_prefix,
    ):
        if not accrual_journal_id:
            accrual_journal_id = self.journal_id.id
        accrual_ref = self._get_accrual_ref(move_prefix)
        move_lines = self.invoice_line_ids._get_accrual_move_line_vals(move_line_prefix)
        move_lines.extend(
            self._get_accrual_move_lines_vals(account, move_prefix, move_line_prefix)
        )
        return {
            "ref": accrual_ref,
            "line_ids": [Command.create(move_line) for move_line in move_lines],
            "journal_id": accrual_journal_id,
            "date": accrual_date,
            "narration": self.narration,
            "company_id": self.company_id.id,
            "to_be_reversed": True,
        }

    def _move_accrual(
        self,
        accrual_date,
        account,
        accrual_journal_id=False,
        move_prefix=False,
        move_line_prefix=False,
    ):
        """
        Create the accrual of a move

        :param accrual_date: when the accrual must be input
        :param accrual_journal_id: facultative journal on which create
                                    the move
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names

        :return: Returns the id of the created accrual move
        """
        self.ensure_one()
        accrual_move = self.create(
            self._get_accrual_move_vals(
                accrual_date, account, accrual_journal_id, move_prefix, move_line_prefix
            )
        )
        # make the invoice point to that move
        self.accrual_move_id = accrual_move
        accrual_move.action_post()
        return accrual_move

    def _post_accrual_move(self, accrual_move_id):
        self.ensure_one()
        # Prevent passing invoice in context in method post: otherwise accrual
        # sequence could be the one from this invoice
        accrual_move_id.with_context(invoice=False).action_post()

    def create_accruals(
        self,
        accrual_date,
        account,
        accrual_journal_id=False,
        move_prefix=False,
        move_line_prefix=False,
    ):
        """
        Create the accrual of one or multiple invoices

        :param accrual_date: when the accrual must be input
        :param account: accrual account
        :param accrual_journal_id: facultative journal on which create
                                    the move
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names

        :return: Returns a list of ids of the created accrual moves
        """

        accrual_moves = self.browse()
        for invoice in self:
            if invoice.state != "draft":
                continue  # skip the accrual creation if state is not draft

            accrual_moves |= invoice._move_accrual(
                accrual_date,
                account,
                accrual_journal_id=accrual_journal_id,
                move_prefix=move_prefix,
                move_line_prefix=move_line_prefix,
            )

        return accrual_moves

    def button_reversal(self):
        self.ensure_one()
        if not self.accrual_move_to_be_reversed:
            return False
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_view_account_move_reversal"
        )
        date = self.date or self.date_invoice
        action.update(
            {
                "context": {
                    "active_model": "account.move",
                    "active_id": self.accrual_move_id.id,
                    "active_ids": [self.accrual_move_id.id],
                    "default_date": date,
                }
            }
        )
        return action
