# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class MealPackage(models.Model):
    _name = "meal.package"
    _description = "Meal Package"

    product_id = fields.Many2one(
        "product.product",
        "Meal Package",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    meal_id = fields.Many2one("res.partner", "Meal", ondelete="restrict")

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
        if context.get("date") and context.get("meal_id"):
            args = []
            contract = self.env["package.contract"].search(
                [
                    ("meal_id", "=", context.get("meal_id")),
                    ("package_contract_type", "=", "meal"),
                    ("date_start", "<=", context.get("date")),
                    ("date_end", ">=", context.get("date")),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            meal_packages = (
                contract.filtered(lambda a: a.meal_id.id == context.get("meal_id"))
                .mapped("meal_contract_lines_ids")
                .mapped("meal_package_id")
            )
            args.append(["id", "in", meal_packages.ids])
        return super(MealPackage, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class MealPackageLine(models.Model):
    _name = "meal.packages.line"
    _description = "Meal Package Line"

    meal_id = fields.Many2one("res.partner", "Meal")
    meal_package_id = fields.Many2one("meal.package", "Meal Package")
    meal_qty = fields.Integer("Quantity")
    unit_price = fields.Float("Unit Price")
    cost_price = fields.Float("Cost Price")
    package_contract_id = fields.Many2one(
        "package.contract", "Contract", ondelete="cascade"
    )
    package_contract_type = fields.Selection(
        related="package_contract_id.package_contract_type", string="Type", store=True
    )

    @api.onchange("meal_package_id")
    def _onchange_meal_package_id(self):
        if self.meal_package_id:
            self.update(
                {
                    "unit_price": self.meal_package_id.lst_price,
                    "cost_price": self.meal_package_id.standard_price,
                }
            )
