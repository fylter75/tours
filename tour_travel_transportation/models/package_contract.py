#  See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PackageContract(models.Model):
    _inherit = "package.contract"

    transportation_id = fields.Many2one(
        "res.partner", "Transportation", ondelete="restrict"
    )
    transportation_contract_line_ids = fields.One2many(
        "package.contract.line",
        "transportation_package_contract_id",
        "Transportation Contract Lines",
        copy=True,
    )
    package_contract_type = fields.Selection(
        selection_add=[("transportation", "Transportation")]
    )

    @api.onchange("city_id", "package_contract_type")
    def _onchange_city_id(self):
        res = super(PackageContract, self)._onchange_city_id()
        if self.city_id and self.package_contract_type == "transportation":
            self.transportation_id = False
            self.partner_id = False
        return res

    @api.onchange("transportation_id")
    def _onchange_transportation_id(self):
        data_list = []
        if self.transportation_id:
            self.partner_id = self.transportation_id.id
            self.transportation_contract_line_ids = [(5,)]
            for line in self.transportation_id.vehicle_line_ids:
                vals = {
                    "vehicle_id": line.vehicle_id.id,
                    "unit_price": line.vehicle_id.standard_price,
                    "capacity": line.vehicle_id.capacity,
                    "sales_price": line.vehicle_id.list_price,
                }
                data_list.append((0, 0, vals))
            self.transportation_contract_line_ids = data_list


class PackageContractLine(models.Model):
    _inherit = "package.contract.line"

    vehicle_id = fields.Many2one("transportation.vehicle", "Vehicle Type")
    transportation_package_contract_id = fields.Many2one(
        "package.contract", "Package Contract"
    )
    package_contract_type = fields.Selection(
        related="transportation_package_contract_id.package_contract_type",
        string="Type",
    )
    transportation_id = fields.Many2one(
        related="transportation_package_contract_id.transportation_id",
        string="Transportation",
    )
    capacity = fields.Integer("Capacity")
    unit_price = fields.Float("Unit Price")
    sales_price = fields.Float("Sales Price")

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.update(
                {
                    "sales_price": self.vehicle_id.list_price,
                    "unit_price": self.vehicle_id.standard_price,
                    "capacity": self.vehicle_id.capacity,
                }
            )
