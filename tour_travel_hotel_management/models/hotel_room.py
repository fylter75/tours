# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HotelRoom(models.Model):
    _name = "hotel.room"
    _description = "Hotel Room"

    product_id = fields.Many2one(
        "product.product",
        " Hotel Room",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    max_adult = fields.Integer("Maximum Adult", default="1")
    max_child = fields.Integer("Maximum Children")
    capacity = fields.Integer("Total Capacity", required=True, default=1)
    hotel_id = fields.Many2one("res.partner", "Hotel")

    @api.constrains("max_adult", "capacity")
    def _check_max_capacity(self):
        for rec in self:
            if rec.max_adult and rec.capacity and rec.capacity < rec.max_adult:
                raise ValidationError(_("Number of Adults can not be more than room capacity."))

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
        if (
            context.get("from_date")
            and context.get("to_date")
            and context.get("hotel_id")
        ):
            args = []
            contract = self.env["package.contract"].search(
                [
                    ("hotel_id", "=", context.get("hotel_id")),
                    ("package_contract_type", "=", "hotel"),
                    ("date_start", "<=", context.get("from_date")),
                    ("date_end", ">=", context.get("to_date")),
                    ("date_start", "<=", context.get("from_date")),
                    ("date_end", ">=", context.get("to_date")),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            rooms = (
                contract.filtered(lambda a: a.hotel_id.id == context.get("hotel_id"))
                .mapped("contract_lines_ids")
                .mapped("room_id")
            )
            args.append(["id", "in", rooms.ids])
        return super(HotelRoom, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class HotelRoomType(models.Model):
    _name = "hotel.room.type"
    _description = "Hotel Room Type"

    name = fields.Char("Name", required=True)


class HotelRoomLine(models.Model):
    _name = "hotel.room.line"
    _rec_name = "room_id"
    _description = "Hotel Room Line"

    hotel_id = fields.Many2one("res.partner", "Hotel", ondelete="cascade")
    room_id = fields.Many2one("hotel.room", "Room", ondelete="restrict", index=True)
    room_type_id = fields.Many2one("hotel.room.type", "Room Type", ondelete="restrict")
    capacity = fields.Integer("Total Capacity", required=True, default=1)
    room_qty = fields.Integer("No of Rooms")
    unit_price = fields.Float("Unit Price")
    cost_price = fields.Float("Cost Price")
    package_contract_id = fields.Many2one(
        "package.contract", "Contract", ondelete="cascade"
    )
    package_contract_type = fields.Selection(
        related="package_contract_id.package_contract_type", string="Type", store=True
    )

    @api.onchange("room_id")
    def _onchange_room_id(self):
        self.update(
            {
                "unit_price": self.room_id.list_price or 0,
                "cost_price": self.room_id.standard_price or 0,
                "capacity": self.room_id.capacity or 0,
            }
        )
