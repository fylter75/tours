# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class TransportationVehicle(models.Model):
    _name = "transportation.vehicle"
    _description = "Transportation Vehicle "

    product_id = fields.Many2one(
        "product.product",
        "Transportation",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    vehicle_number = fields.Char("Vehicle Number")
    capacity = fields.Integer("Capacity")

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
        if context.get("journey_date") and context.get("transportation_id"):
            args = []
            contract = self.env["package.contract"].search(
                [
                    ("transportation_id", "=", context.get("transportation_id")),
                    ("package_contract_type", "=", "transportation"),
                    ("date_start", "<=", context.get("journey_date")),
                    ("date_end", ">=", context.get("journey_date")),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            vehicles = (
                contract.filtered(
                    lambda a: a.transportation_id.id == context.get("transportation_id")
                )
                .mapped("transportation_contract_line_ids")
                .mapped("vehicle_id")
            )
            args.append(["id", "in", vehicles.ids])
        return super(TransportationVehicle, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class TransportationVehicleLine(models.Model):
    _name = "transportation.vehicle.line"
    _rec_name = "vehicle_id"
    _description = "Transportation Vehicle Line"

    transportation_id = fields.Many2one("res.partner", "Transportation")
    vehicle_id = fields.Many2one("transportation.vehicle", "Vehicle Type")
    qty = fields.Integer("Quantity")
    cost_price = fields.Float("Cost Price")
    unit_price = fields.Float("Unit Price")
    capacity = fields.Integer("Capacity")

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.update(
                {
                    "unit_price": self.vehicle_id.list_price,
                    "cost_price": self.vehicle_id.standard_price,
                    "capacity": self.vehicle_id.capacity,
                }
            )
