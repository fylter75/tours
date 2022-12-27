# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class MealRegistration(models.Model):
    _inherit = "res.partner"
    _description = "Meal Registration"

    @api.depends("meal_contract_ids")
    def _compute_meal_contract_count(self):
        contract_obj = self.env["package.contract"]
        for meal in self:
            meal.meal_contract_count = contract_obj.search_count(
                [("package_contract_type", "=", "meal"), ("meal_id", "=", meal.id)]
            )

    def _compute_running_contract(self):
        contract_obj = self.env["package.contract"]
        res = super(MealRegistration, self)._compute_running_contract()
        for meal in self:
            running_contract = contract_obj.search_count(
                [("meal_id", "=", meal.id), ("state", "=", "open")]
            )
            if running_contract != 0:
                meal.update({"is_contract_running": True})
        return res

    meal_package_line_ids = fields.One2many(
        "meal.packages.line", "meal_id", string="Meal Packages"
    )
    is_restaurant = fields.Boolean("Is Restaurant")
    meal_contract_count = fields.Integer(
        "Meal Contract", compute="_compute_meal_contract_count"
    )
    meal_contract_ids = fields.One2many("package.contract", "meal_id", "Meal Contracts")

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        args = args or []
        context = dict(self._context) or {}
        if context.get("city_id") and context.get("package_contract_type") == "meal":
            args = [
                ("city_id", "=", context.get("city_id")),
                ("registration_type", "=", "hotel"),
                ("is_restaurant", "=", True),
            ]
        return super(MealRegistration, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
