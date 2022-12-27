#  See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

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
            and context.get("city_id")
        ):
            contracts = self.env["package.contract"].search(
                [
                    ("package_contract_type", "=", "hotel"),
                    ("date_start", "<=", context.get("from_date")),
                    ("date_end", ">=", context.get("to_date")),
                    ("date_start", "<=", context.get("from_date")),
                    ("date_end", ">=", context.get("to_date")),
                ]
            )
            hotels = contracts.filtered(
                lambda a: a.hotel_id.city_id.id == context.get("city_id")
            ).mapped("hotel_id")
            args.append(["id", "in", hotels.ids])
        return super(ResPartner, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class SaleOrderTemplete(models.Model):
    _inherit = "sale.order.template"

    def get_cost_price(self):
        res = super(SaleOrderTemplete, self).get_cost_price()
        hotel_price = 0.0
        for order in self:
            hotel_price = sum(
                [
                    hotel_line.cost_price * hotel_line.stay_days
                    for hotel_line in order.hotel_package_line_ids
                    if hotel_line.room_type_id.capacity != 0
                ]
            )
        return res + hotel_price

    def get_sell_price(self):
        res = super(SaleOrderTemplete, self).get_sell_price()
        hotel_sell_price = 0.0
        for order in self:
            hotel_sell_price = sum(
                [
                    hotel_line.price_unit * hotel_line.stay_days
                    for hotel_line in order.hotel_package_line_ids
                    if hotel_line.room_type_id.capacity != 0
                ]
            )
        return res + hotel_sell_price

    @api.depends("hotel_package_line_ids.cost_price")
    def _compute_cost_per_person(self):
        for order in self:
            total_cost = self.get_cost_price()
            order.update({"cost_per_person": total_cost})

    @api.depends("hotel_package_line_ids.cost_price")
    def _compute_sell_per_person(self):
        for order in self:
            total_sale_price = self.get_sell_price()
            order.update({"sell_per_person": total_sale_price})

    hotel_package_line_ids = fields.One2many(
        "hotel.package.line", "sale_order_templete_id", string="Hotel Package Lines"
    )

    def action_generate_itinerary_plan(self):
        super(SaleOrderTemplete, self).action_generate_itinerary_plan()
        hotel = []
        for line in self.hotel_package_line_ids:
            from_date = line.from_date
            to_date = line.to_date
            for itinerary in self.itinerary_ids:
                if from_date == to_date + relativedelta(days=+1):
                    break
                while itinerary.itinerary_date == from_date:
                    hotel.append(line.id)
                    from_date = from_date + relativedelta(days=+1)
                    itinerary.hotel_ids = hotel
                    itinerary.name = "{desc} \n {name}{hotel_name}".format(
                        desc=itinerary.name, name="Hotel :", hotel_name=line.name
                    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    hotel_line_ids = fields.One2many(
        "tour.registration.line", "hotel_sale_id", "Hotel Lines"
    )

    def get_package_hotel_lines(self):
        package_lines = []
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        for line in template.hotel_package_line_ids:
            data = {
                "name": line.display_name,
                "stay_days": 0,
                "display_type": line.display_type,
            }
            pax_qty = 1
            total_pax = self.adults + self.children
            if total_pax > 1:
                pax_qty = total_pax
            if not line.display_type:
                data = {
                    "name": line.display_name,
                    "from_date": line.from_date,
                    "to_date": line.to_date,
                    "hotel_id": line.hotel_id.id,
                    "city_id": line.city_id.id,
                    "display_type": line.display_type,
                    "room_type_id": line.room_type_id.id,
                    "stay_days": line.stay_days,
                    "room_qty": line.qty * pax_qty,
                    "product_uom_qty": line.qty,
                    "purchase_price": line.cost_price,
                    "price_unit": line.price_unit,
                    "product_id": line.room_type_id.product_id.id,
                    "product_uom": line.room_type_id.product_id.uom_id.id,
                    "customer_lead": self._get_customer_lead(
                        line.room_type_id.product_id.product_tmpl_id
                    ),
                }
            package_lines.append((0, 0, data))
        return package_lines

    @api.onchange("sale_order_template_id")
    def onchange_sale_order_template_id(self):
        order_lines = self.get_package_hotel_lines()
        self.hotel_line_ids = [(5,)]
        self.update({"hotel_line_ids": order_lines})
        for rec in self.hotel_line_ids:
            if not rec.display_type:
                rec._onchange_room_qty()
                rec._compute_tax_id()
        return super(SaleOrder, self).onchange_sale_order_template_id()


class TourRegistrationLine(models.Model):
    _inherit = "tour.registration.line"

    @api.depends("from_date", "to_date")
    def _compute_no_days(self):
        for rec in self:
            if rec.from_date and rec.to_date:
                rec.stay_days = (rec.to_date - rec.from_date).days

    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")
    hotel_sale_id = fields.Many2one("sale.order", "Order", ondelete="cascade")
    city_id = fields.Many2one("city.city", "City", index=True)
    hotel_id = fields.Many2one("res.partner", "Hotel", ondelete="restrict", index=True)
    room_type_id = fields.Many2one("hotel.room", "Room Type", ondelete="restrict")
    room_qty = fields.Integer(string="No of Room", default=1)
    stay_days = fields.Integer(
        compute="_compute_no_days", string="Duration", store=True
    )

    @api.model
    def create(self, vals):
        if "hotel_sale_id" in vals:
            sale = self.env["sale.order"].browse(vals["hotel_sale_id"])
            vals.update({"order_id": sale.id})
        return super(TourRegistrationLine, self).create(vals)

    @api.onchange("from_date", "to_date", "city_id")
    def _onchange_from_to_date(self):
        self.update(
            {"hotel_id": False, "contract_id": False, "room_type_id": False, "name": ""}
        )

    @api.onchange("hotel_id")
    def _onchange_hotel_id(self):
        change_contract = {"contract_id": False, "room_type_id": False}
        if self.hotel_id and self.from_date and self.to_date:
            contract = self.env["package.contract"].search(
                [
                    ("hotel_id", "=", self.hotel_id.id),
                    ("package_contract_type", "=", "hotel"),
                    ("date_start", "<=", self.from_date),
                    ("date_end", ">=", self.to_date),
                    ("date_start", "<=", self.from_date),
                    ("date_end", ">=", self.to_date),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            change_contract = {"contract_id": contract.id}
        self.update(change_contract)

    def _get_product_descripation(self):
        res = super(TourRegistrationLine, self)._get_product_descripation()
        if self.hotel_id and self.room_type_id:
            name = ""
            name += "Hotel : {},{}".format(self.hotel_id.name, self.city_id.name)
            name += "\n" + "Room Type: {}".format(self.room_type_id.name)
            name += "\n" + "Qty : {} => {} (Stays) * {} (Room Qty)".format(
                self.stay_days * self.room_qty, self.stay_days, self.room_qty,
            )
            return name
        return res

    @api.onchange("room_qty", "stay_days")
    def _onchange_room_qty(self):
        for rec in self:
            rec.product_uom_qty = rec.room_qty * rec.stay_days
            rec.name = rec._get_product_descripation()

    def _get_hotel_contract_line(self):
        contract_line = self.contract_id.mapped("contract_lines_ids").filtered(
            lambda a: a.room_id == self.room_type_id
        )
        return contract_line

    def _get_contract_price(self):
        res = super(TourRegistrationLine, self)._get_contract_price()
        if self.room_type_id and self.contract_id:
            contract_line = self._get_hotel_contract_line()
            res = contract_line.sales_price / contract_line.capacity
        return res

    def _get_contract_cost_price(self):
        res = super(TourRegistrationLine, self)._get_contract_cost_price()
        if self.room_type_id and self.contract_id:
            contract_line = self._get_hotel_contract_line()
            res = contract_line.unit_price / contract_line.capacity
        return res

    @api.onchange("room_type_id")
    def _onchange_room_type(self):
        if self.room_type_id:
            self.update(
                {
                    "product_id": self.room_type_id.product_id.id,
                    "order_id": self.hotel_sale_id.id,
                }
            )
            self._onchange_room_qty()

    @api.constrains("from_date", "to_date")
    def _check_duration_range(self):
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise ValidationError(_("From date should be greater than to date!"))
            elif fields.Date.today() > self.from_date:
                raise ValidationError(
                    _("From date should be greater than current date!")
                )
            elif (self.from_date < self.order_id.tour_begin_date < self.to_date) or (
                self.from_date < self.order_id.tour_end_date < self.to_date
            ):
                raise ValidationError(
                    _("From date/To date should in between Arrival/Departure date!")
                )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    hotel_id = fields.Many2one("hotel.package.line", "Hotel")


class HotelPackageLine(models.Model):
    _name = "hotel.package.line"
    _description = "Hotel Package Line"

    @api.depends("from_date", "to_date")
    def _compute_no_days(self):
        for rec in self:
            if rec.from_date and rec.to_date:
                rec.stay_days = (rec.to_date - rec.from_date).days

    @api.depends("qty", "price_unit", "stay_days")
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.qty * line.price_unit * line.stay_days

    name = fields.Text("Description", translate=True)
    hotel_id = fields.Many2one("res.partner", "Hotel")
    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")
    city_id = fields.Many2one("city.city", "City")
    state_id = fields.Many2one(
        "res.country.state",
        "State",
        related="sale_order_templete_id.state_id",
        store=True,
    )
    room_type_id = fields.Many2one("hotel.room", "Room Type")
    stay_days = fields.Integer(
        compute="_compute_no_days", string="Duration", readonly=True, store=True
    )
    qty = fields.Float("Room Qty", required=True, default=1.0)
    cost_price = fields.Float(
        "Cost Price", required=True, digits="Product Price", default=0.0
    )
    price_unit = fields.Float(
        "Unit Price", required=True, digits="Product Price", default=0.0
    )
    price_subtotal = fields.Float(
        "Subtotal", compute="_compute_amount", readonly=True, store=True
    )
    sale_order_templete_id = fields.Many2one("sale.order.template", string="Sale Order")
    contract_id = fields.Many2one("package.contract", "Contract")
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )
    sequence = fields.Integer()

    @api.onchange("from_date", "to_date", "city_id")
    def _onchange_from_to_date(self):
        self.update(
            {"hotel_id": False, "contract_id": False, "room_type_id": False, "name": ""}
        )

    @api.onchange("hotel_id")
    def _onchange_hotel_id(self):
        change_contract = {"contract_id": False, "room_type_id": False}
        if (
            self.hotel_id
            and self.sale_order_templete_id
            and self.sale_order_templete_id.arrival_date
            and self.sale_order_templete_id.return_date
        ):
            contract = self.env["package.contract"].search(
                [
                    ("hotel_id", "=", self.hotel_id.id),
                    ("package_contract_type", "=", "hotel"),
                    ("date_start", "<=", self.sale_order_templete_id.arrival_date),
                    ("date_end", ">=", self.sale_order_templete_id.arrival_date),
                    ("date_start", "<=", self.sale_order_templete_id.return_date),
                    ("date_end", ">=", self.sale_order_templete_id.return_date),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            change_contract = {"contract_id": contract.id}
        self.update(change_contract)

    def _get_product_description(self):
        if self.hotel_id and self.room_type_id:
            name = ""
            name += "Hotel : {},{}".format(self.hotel_id.name, self.city_id.name)
            name += "\n" + "Room Type: {}".format(self.room_type_id.name)
            return name

    @api.onchange("room_type_id")
    def _onchange_room_type(self):
        if self.room_type_id:
            for rec in self:
                rec.name = rec._get_product_description()

        if self.room_type_id and self.contract_id:
            contract_line = self.contract_id.mapped("contract_lines_ids").filtered(
                lambda a: a.room_id == self.room_type_id
            )
            self.update(
                {
                    "price_unit": (
                        (
                            contract_line.sales_price
                            or self.room_type_id.product_id.lst_price
                        )
                        / contract_line.capacity
                    ),
                    "cost_price": (
                        (
                            contract_line.unit_price
                            or self.room_type_id.product_id.standard_price
                        )
                        / contract_line.capacity
                    ),
                }
            )


class PackageItinerary(models.Model):
    _inherit = "package.itinerary"

    hotel_ids = fields.Many2many("hotel.package.line", string="Hotel")
