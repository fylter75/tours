#  See LICENSE file for full copyright and licensing details.
import collections

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PackageContract(models.Model):
    _inherit = "package.contract"

    hotel_id = fields.Many2one("res.partner", string="Hotel", ondelete="restrict")
    room_ids = fields.One2many(
        "hotel.room.line", "package_contract_id", string="Room Information"
    )
    contract_lines_ids = fields.One2many(
        "package.contract.line",
        "hotel_package_contract_id",
        "Contract Lines",
        copy=True,
    )
    package_contract_type = fields.Selection(
        selection_add=[("hotel", "Hotel")], ondelete={"hotel": "cascade"}
    )

    @api.constrains("contract_lines_ids")
    def _unique_room_ids(self):
        if not self.contract_lines_ids and self.package_contract_type == "hotel":
            raise ValidationError(_("You need to add contract lines"))

        for contract in self:
            room_ids = [line.room_id.id for line in contract.contract_lines_ids]
            duplicate = [
                item
                for item, count in collections.Counter(room_ids).items()
                if count > 1
            ]
            if duplicate:
                raise ValidationError(
                    _("You can not have same rooms in contract lines")
                )

        return True

    @api.onchange("city_id", "package_contract_type")
    def _onchange_city_id(self):
        res = super(PackageContract, self)._onchange_city_id()
        if self.city_id and self.package_contract_type == "hotel":
            self.hotel_id = False
            self.partner_id = False
        return res

    @api.onchange("hotel_id")
    def _onchange_hotel_id(self):
        data_list = []
        self.contract_lines_ids = [(5,)]
        if self.hotel_id:
            self.partner_id = self.hotel_id.id
            for line in self.hotel_id.room_line_ids:
                vals = {
                    "room_id": line.room_id.id,
                    "room_type_id": line.room_type_id.id,
                    "capacity": line.capacity,
                    "room_qty": line.room_qty,
                    "unit_price": line.room_id.standard_price,
                    "sales_price": line.room_id.list_price,
                }
                data_list.append((0, 0, vals))
            self.contract_lines_ids = data_list


class PackageContractLine(models.Model):
    _inherit = "package.contract.line"

    room_id = fields.Many2one("hotel.room", "Room")
    room_type_id = fields.Many2one("hotel.room.type", "Room Type")
    capacity = fields.Integer("Total Capacity", required=True, default=1)
    room_qty = fields.Integer("No of Rooms")
    unit_price = fields.Float("Unit Price")
    sales_price = fields.Float("Sales Price")
    hotel_package_contract_id = fields.Many2one(
        "package.contract", "Contract", ondelete="cascade"
    )
    package_contract_type = fields.Selection(
        related="hotel_package_contract_id.package_contract_type", string="Type"
    )
    hotel_id = fields.Many2one(
        related="hotel_package_contract_id.hotel_id", string="Hotel"
    )
