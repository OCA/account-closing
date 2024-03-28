from odoo import fields, models


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
    )

    revaluation_origin_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="revaluation_created_line_id",
        string="Revaluation Origin Lines",
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
