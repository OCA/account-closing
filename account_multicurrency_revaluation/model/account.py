# Copyright 2012-2018 Camptocamp SA
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccountLine(models.Model):
    _inherit = "account.move.line"
    # By convention added columns start with gl_.
    gl_foreign_balance = fields.Float(string="Aggregated Amount currency")
    gl_balance = fields.Float(string="Aggregated Amount")
    gl_revaluated_balance = fields.Float(string="Revaluated Amount")
    gl_currency_rate = fields.Float(string="Currency rate")

    revaluation_created_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Revaluation Created Line",
        readonly=True,
    )

    revaluation_origin_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="revaluation_created_line_id",
        string="Revaluation Origin Lines",
        readonly=True,
    )
    revaluation_origin_line_count = fields.Integer(
        compute="_compute_revaluation_origin_line_count"
    )

    def _compute_revaluation_origin_line_count(self):
        for line in self:
            line.revaluation_origin_line_count = len(line.revaluation_origin_line_ids)

    def action_view_revaluation_origin_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_account_moves_all"
        )
        action["context"] = {}
        if len(self.revaluation_origin_line_ids) > 1:
            action["domain"] = [("id", "in", self.revaluation_origin_line_ids.ids)]
        elif self.revaluation_origin_line_ids:
            form_view = [(self.env.ref("account.view_move_line_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = self.revaluation_origin_line_ids.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def action_view_revaluation_created_line(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_account_moves_all"
        )
        action["context"] = {}
        if self.revaluation_created_line_id:
            form_view = [(self.env.ref("account.view_move_line_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = self.revaluation_created_line_id.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action


class AccountAccount(models.Model):
    _inherit = "account.account"

    currency_revaluation = fields.Boolean(
        string="Allow Currency Revaluation",
    )

    _sql_mapping = {
        "balance": "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
        "debit": "COALESCE(SUM(debit), 0) as debit",
        "credit": "COALESCE(SUM(credit), 0) as credit",
        "foreign_balance": "COALESCE(SUM(amount_currency), 0) as foreign_balance",
    }

    def init(self):
        # all receivable, payable, Bank and Cash accounts should
        # have currency_revaluation True by default
        res = super().init()
        accounts = self.env["account.account"].search(
            [
                ("user_type_id.id", "in", self._get_revaluation_account_types()),
                ("currency_revaluation", "=", False),
                ("user_type_id.include_initial_balance", "=", True),
            ]
        )
        accounts.write({"currency_revaluation": True})
        return res

    def write(self, vals):
        if (
            "currency_revaluation" in vals
            and vals.get("currency_revaluation", False)
            and any(
                [not x for x in self.mapped("user_type_id.include_initial_balance")]
            )
        ):
            raise UserError(
                _(
                    "There is an account that you are editing not having the Bring "
                    "Balance Forward set, the currency revaluation cannot be applied "
                    "on these accounts: \n\t - %s"
                )
                % "\n\t - ".join(
                    self.filtered(
                        lambda x: not x.user_type_id.include_initial_balance
                    ).mapped("name")
                )
            )
        return super(AccountAccount, self).write(vals)

    def _get_revaluation_account_types(self):
        return [
            self.env.ref("account.data_account_type_receivable").id,
            self.env.ref("account.data_account_type_payable").id,
            self.env.ref("account.data_account_type_liquidity").id,
        ]

    @api.onchange("user_type_id")
    def _onchange_user_type_id(self):
        revaluation_accounts = self._get_revaluation_account_types()
        for rec in self:
            if rec.user_type_id.id in revaluation_accounts:
                rec.currency_revaluation = True

    def _revaluation_query(self, revaluation_date, start_date=None):
        tables, where_clause, where_clause_params = self.env[
            "account.move.line"
        ]._query_get()
        mapping = [
            ('"account_move_line".', "aml."),
            ('"account_move_line"', "account_move_line aml"),
            ("LEFT JOIN", "\n    LEFT JOIN"),
            (")) AND", "))\n" + " " * 12 + "AND"),
        ]
        for s_from, s_to in mapping:
            tables = tables.replace(s_from, s_to)
            where_clause = where_clause.replace(s_from, s_to)
        where_clause = ("\n" + " " * 8 + "AND " + where_clause) if where_clause else ""
        query = (
            """
WITH amount AS (
    SELECT
        aml.account_id,
        CASE WHEN aat.type IN ('payable', 'receivable')
            THEN aml.partner_id
            ELSE NULL
        END AS partner_id,
        aml.currency_id,
        aml.debit,
        aml.credit,
        aml.amount_currency,
        aml.id as origin_aml_id
    FROM """
            + tables
            + """
    LEFT JOIN account_move am ON aml.move_id = am.id
    INNER JOIN account_account acc ON aml.account_id = acc.id
    INNER JOIN account_account_type aat ON acc.user_type_id = aat.id
    LEFT JOIN account_partial_reconcile aprc
        ON (aml.balance < 0 AND aml.id = aprc.credit_move_id)
    LEFT JOIN account_move_line amlcf
        ON (
            aml.balance < 0
            AND aprc.debit_move_id = amlcf.id
            AND amlcf.date < %s
        )
    LEFT JOIN account_partial_reconcile aprd
        ON (aml.balance > 0 AND aml.id = aprd.debit_move_id)
    LEFT JOIN account_move_line amldf
        ON (
            aml.balance > 0
            AND aprd.credit_move_id = amldf.id
            AND amldf.date < %s
        )
    WHERE
        aml.account_id IN %s
        AND aml.date <= %s
        """
            + (("AND aml.date >= %s") if start_date else "")
            + """
        AND aml.currency_id IS NOT NULL
        AND am.state = 'posted'
        AND aml.balance <> 0
        """
            + where_clause
            + """
    GROUP BY
        aat.type,
        origin_aml_id
    HAVING
        aml.amount_residual_currency <> 0
)
SELECT
    account_id as id,
    origin_aml_id,
    partner_id,
    currency_id,"""
            + ", ".join(self._sql_mapping.values())
            + """
FROM amount
GROUP BY
    account_id,
    origin_aml_id,
    currency_id,
    partner_id
ORDER BY account_id, partner_id, currency_id"""
        )

        params = [
            revaluation_date,
            revaluation_date,
            tuple(self.ids),
            revaluation_date,
            *where_clause_params,
        ]
        if start_date:
            # Insert the value after the revaluation date parameter
            params.insert(4, start_date)

        return query, params

    def compute_revaluations(self, revaluation_date, start_date=None):
        query, params = self._revaluation_query(revaluation_date, start_date)
        self.env.cr.execute(query, params)
        lines = self.env.cr.dictfetchall()

        data = {}
        for line in lines:
            account_id, currency_id, partner_id, origin_aml_id = (
                line["id"],
                line["currency_id"],
                line["partner_id"],
                line["origin_aml_id"],
            )
            data.setdefault(account_id, {})
            data[account_id].setdefault(partner_id, {})
            data[account_id][partner_id].setdefault(currency_id, {})
            # If partially reconciled, we need to adjust the balance according to
            # the partially reconciled items on the current line.
            origin_aml = self.env["account.move.line"].browse(origin_aml_id)
            if origin_aml.matched_debit_ids | origin_aml.matched_credit_ids:
                debit_move_ids = origin_aml.matched_debit_ids.mapped("debit_move_id")
                credit_move_ids = origin_aml.matched_credit_ids.mapped("credit_move_id")
                total_debit = line["debit"] + sum(debit_move_ids.mapped("debit"))
                total_credit = line["credit"] + sum(credit_move_ids.mapped("credit"))
                total_balance = total_debit - total_credit
                total_balance_currency = (
                    line["foreign_balance"]
                    + sum(debit_move_ids.mapped("amount_currency"))
                    + sum(credit_move_ids.mapped("amount_currency"))
                )
                line.update(
                    {
                        "debit": round(total_debit, 2),
                        "credit": round(total_credit, 2),
                        "balance": round(total_balance, 2),
                        "foreign_balance": round(total_balance_currency, 2),
                    }
                )
            existing_line = data[account_id][partner_id][currency_id]
            if existing_line:
                data[account_id][partner_id][
                    currency_id
                ] = self._merge_currency_revaluation_lines(existing_line, line)
            else:
                # Convert origin account move lines to list as there can be multiple
                line["origin_aml_id"] = [line["origin_aml_id"]]
                data[account_id][partner_id][currency_id] = line
        return data

    @api.model
    def _merge_currency_revaluation_lines(self, first_line, second_line):
        resulting_line = first_line
        resulting_line["origin_aml_id"].append(second_line["origin_aml_id"])
        resulting_line["balance"] += second_line["balance"]
        resulting_line["debit"] += second_line["debit"]
        resulting_line["credit"] += second_line["credit"]
        resulting_line["foreign_balance"] += second_line["foreign_balance"]
        return resulting_line


class AccountMove(models.Model):
    _inherit = "account.move"

    revaluation_to_reverse = fields.Boolean(
        string="Revaluation to reverse", default=False, readonly=True
    )

    revaluation_reversed = fields.Boolean(
        string="Revaluation reversed", default=False, readonly=True
    )
