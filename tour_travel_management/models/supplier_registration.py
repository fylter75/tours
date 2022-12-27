#  See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Partner(models.Model):
    _inherit = "res.partner"

    @api.depends("contract_ids", "contract_ids.state")
    def _compute_running_contract(self):
        for rec in self:
            rec.update({"is_contract_running": False})

    date_of_birth = fields.Date("Birth Date")
    date_of_anniversary = fields.Date("Anniversary Date")
    registration_type = fields.Selection([], " Registration Type")
    is_contract_running = fields.Boolean(
        "Contract Running", compute="_compute_running_contract", store=True
    )
    city_id = fields.Many2one("city.city", "Partner City")
    rating = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Very High")],
        string="Rating",
    )
    contract_ids = fields.One2many("package.contract", "partner_id", "Contract")

    @api.constrains("date_of_birth", "date_of_anniversary")
    def _check_birth_anniversary_date(self):
        current_date = fields.Date.context_today(self)
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > current_date:
                raise ValidationError(
                    _("""Birth Date should be smaller than Current Date.""")
                )
            if rec.date_of_anniversary and rec.date_of_anniversary > current_date:
                raise ValidationError(
                    _("""Anniversary Date should be smaller than Current Date.""")
                )

    @api.onchange("city_id")
    def _onchange_city(self):
        if self.city_id:
            self.update(
                {
                    "zip": self.city_id.zip,
                    "state_id": self.city_id.state_id.id,
                    "country_id": self.city_id.state_id.country_id.id,
                }
            )
