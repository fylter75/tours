#  See LICENSE file for full copyright and licensing details.
import collections

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PackageContract(models.Model):
    _inherit = "package.contract"

    meal_id = fields.Many2one("res.partner", string="Meal", ondelete="restrict")
    meal_package_ids = fields.One2many(
        "meal.packages.line", "package_contract_id", string="Meal Information"
    )
    meal_contract_lines_ids = fields.One2many(
        "package.contract.line",
        "meal_package_contract_id",
        "Meal Contract Lines",
        copy=True,
    )
    package_contract_type = fields.Selection(selection_add=[("meal", "Meal")])

    @api.constrains("meal_contract_lines_ids")
    def unique_meal_package_ids(self):
        for contract in self:
            meal_package_ids = []
            for line in contract.meal_contract_lines_ids:
                meal_package_ids.append(line.meal_package_id.id)
            duplicate = [
                item
                for item, count in collections.Counter(meal_package_ids).items()
                if count > 1
            ]
            if duplicate:
                raise ValidationError(
                    _("You can not have same package in contract lines")
                )
        return True

    @api.onchange("city_id", "package_contract_type")
    def _onchange_city_id(self):
        res = super(PackageContract, self)._onchange_city_id()
        if self.city_id and self.package_contract_type == "meal":
            self.meal_id = False
            self.partner_id = False
        return res

    @api.onchange("meal_id")
    def _onchange_meal_id(self):
        data_list = []
        if self.meal_id:
            self.partner_id = self.meal_id.id
            self.meal_contract_lines_ids = [(5,)]
            for line in self.meal_id.meal_package_line_ids:
                vals = {
                    "meal_package_id": line.meal_package_id.id,
                    "meal_package_qty": line.meal_qty,
                    "unit_price": line.meal_package_id.standard_price,
                    "sales_price": line.meal_package_id.list_price,
                }
                data_list.append((0, 0, vals))
            self.meal_contract_lines_ids = data_list


class PackageContractLine(models.Model):
    _inherit = "package.contract.line"

    meal_package_id = fields.Many2one("meal.package", "Meal Package")
    meal_package_qty = fields.Integer("Meal Quantity")
    meal_package_contract_id = fields.Many2one(
        "package.contract", "Meal Contract", ondelete="cascade"
    )
    package_contract_type = fields.Selection(
        related="meal_package_contract_id.package_contract_type", string="Type"
    )
    meal_id = fields.Many2one(related="meal_package_contract_id.meal_id", string="Meal")
