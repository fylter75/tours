#  See LICENSE file for full copyright and licensing details.
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
        if context.get("date") and context.get("city_id"):
            contracts = self.env["package.contract"].search(
                [
                    ("package_contract_type", "=", "meal"),
                    ("date_start", "<=", context.get("date")),
                    ("date_end", ">=", context.get("date")),
                ]
            )
            meals = contracts.filtered(
                lambda a: a.meal_id.city_id.id == context.get("city_id")
            ).mapped("meal_id")
            args.append(["id", "in", meals.ids])
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
        for order in self:
            meal_price = sum(
                [
                    meal_line.cost_price * meal_line.qty
                    for meal_line in order.meal_package_line_ids
                    if meal_line.qty != 0
                ]
            )
        return res + meal_price

    def get_sell_price(self):
        res = super(SaleOrderTemplete, self).get_sell_price()
        for order in self:
            meal_sell_price = sum(
                [
                    meal_line.price_unit * meal_line.qty
                    for meal_line in order.meal_package_line_ids
                    if meal_line.qty != 0
                ]
            )
        return res + meal_sell_price

    @api.depends("meal_package_line_ids.cost_price")
    def _compute_cost_per_person(self):
        for order in self:
            total_cost = self.get_cost_price()
            order.update({"cost_per_person": total_cost})

    @api.depends("meal_package_line_ids.price_unit")
    def _compute_sell_per_person(self):
        for order in self:
            total_sale_price = self.get_sell_price()
            order.update({"sell_per_person": total_sale_price})

    meal_package_line_ids = fields.One2many(
        "template.meal.package.line",
        "sale_order_templete_id",
        string="Meal Package Lines",
    )

    def action_generate_itinerary_plan(self):
        super(SaleOrderTemplete, self).action_generate_itinerary_plan()
        meal = []
        for line in self.meal_package_line_ids:
            meal_date = line.date
            meal_name = line.name
            for itinerary in self.itinerary_ids:
                name = itinerary.name
                if itinerary.itinerary_date == meal_date:
                    meal.append(line.id)
                    itinerary.meal_ids = meal
                    # itinerary.name = (
                    #     itinerary.name + "\n" + "Meal :" + line.name
                    # )
                    if meal_name:
                        name += "\n" + "Meal :" + line.name
                itinerary.name = name


class SaleOrder(models.Model):
    _inherit = "sale.order"

    meal_line_ids = fields.One2many(
        "tour.registration.line", "meal_sale_id", "Meal Lines"
    )

    def get_package_meal_lines(self):
        package_lines = []
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        for line in template.meal_package_line_ids:
            data = {"name": line.display_name, "display_type": line.display_type}
            pax_qty = 1
            total_pax = self.adults + self.children
            if total_pax > 1:
                pax_qty = total_pax
            if not line.display_type:
                data = {
                    "date": line.date,
                    "meal_id": line.meal_id.id,
                    "city_id": line.city_id.id,
                    "display_type": line.display_type,
                    "meal_package_id": line.meal_package_id.id,
                    "meal_qty": line.qty * pax_qty,
                    "product_uom_qty": line.qty,
                    "purchase_price": line.cost_price,
                    "price_unit": line.price_unit,
                    "product_id": line.meal_package_id.product_id.id,
                    "product_uom": line.meal_package_id.product_id.uom_id.id,
                    "customer_lead": self._get_customer_lead(
                        line.meal_package_id.product_id.product_tmpl_id
                    ),
                }
            package_lines.append((0, 0, data))
        return package_lines

    @api.onchange("sale_order_template_id")
    def onchange_sale_order_template_id(self):
        order_lines = self.get_package_meal_lines()
        self.meal_line_ids = [(5, 0, 0)]
        self.update({"meal_line_ids": order_lines})
        for rec in self.meal_line_ids:
            if not rec.display_type:
                rec._onchange_meal_qty()
                rec._compute_tax_id()
        return super(SaleOrder, self).onchange_sale_order_template_id()


class TourRegistrationLine(models.Model):
    _inherit = "tour.registration.line"

    date = fields.Date("Date")
    meal_sale_id = fields.Many2one("sale.order", "Meal Order", ondelete="cascade")
    city_id = fields.Many2one("city.city", "City", index=True)
    meal_id = fields.Many2one("res.partner", "Meal", ondelete="restrict", index=True)
    meal_package_id = fields.Many2one(
        "meal.package", "Meal Package", ondelete="restrict"
    )
    meal_qty = fields.Integer(string="Meal Qty", default=1)

    @api.model
    def create(self, vals):
        if "meal_sale_id" in vals:
            sale = self.env["sale.order"].browse(vals["meal_sale_id"])
            vals.update({"order_id": sale.id})
        return super(TourRegistrationLine, self).create(vals)

    @api.onchange("date", "city_id")
    def _onchange_date_city(self):
        self.meal_id = False

    @api.onchange("meal_id")
    def _onchange_meal_id(self):
        self.meal_package_id = False
        if self.meal_id and self.date:
            contract = self.env["package.contract"].search(
                [
                    ("meal_id", "=", self.meal_id.id),
                    ("package_contract_type", "=", "meal"),
                    ("date_start", "<=", self.date),
                    ("date_end", ">=", self.date),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            self.update({"contract_id": contract.id})

    @api.onchange("meal_qty")
    def _onchange_meal_qty(self):
        for rec in self:
            if rec.meal_qty:
                rec.product_uom_qty = rec.meal_qty
                rec.name = rec.set_meal_description() or rec.name

    def set_meal_description(self):
        if self.meal_id and self.meal_package_id:
            name = ""
            name += "Meal : {},{}".format(self.meal_id.name, self.city_id.name)
            name += "\n" + "MEal Package: %s" % (self.meal_package_id.name)
            name += "\n" + "Qty : %s" % (self.meal_qty)
            return name

    def _get_meal_contract_line(self):
        contract_line = self.contract_id.mapped("meal_contract_lines_ids").filtered(
            lambda a: a.meal_package_id.id == self.meal_package_id.id
        )
        return contract_line

    def _get_contract_price(self):
        res = super(TourRegistrationLine, self)._get_contract_price()
        if self.meal_package_id and self.contract_id:
            contract_line = self._get_meal_contract_line()
            res = contract_line.sales_price
        return res

    def _get_contract_cost_price(self):
        res = super(TourRegistrationLine, self)._get_contract_cost_price()
        if self.meal_package_id and self.contract_id:
            contract_line = self._get_meal_contract_line()
            res = contract_line.unit_price
        return res

    @api.onchange("meal_package_id")
    def onchange_meal_package(self):
        if self.meal_package_id:
            self.update(
                {
                    "product_id": self.meal_package_id.product_id.id,
                    "order_id": self.meal_sale_id.id,
                }
            )
            self.product_id_change()
            self._onchange_meal_qty()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    meal_id = fields.Many2one("template.meal.package.line", "Meal")


class MealPackageLine(models.Model):
    _name = "template.meal.package.line"
    _description = "Template Meal Package Line"

    @api.depends("qty", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.qty * line.price_unit

    name = fields.Text("Description", translate=True)
    date = fields.Date("Date")
    meal_id = fields.Many2one("res.partner", "Restaurant")
    meal_package_id = fields.Many2one("meal.package", "Meal Package")
    city_id = fields.Many2one("city.city", "City")
    product_id = fields.Many2one("product.product", "Meal")
    supplier_id = fields.Many2one("res.partner", "Supplier")
    qty = fields.Float("Qty", required=True, default=1.0)
    contract_id = fields.Many2one("package.contract", "Contract")
    price_unit = fields.Float(
        "Unit Price", required=True, digits="Product Price", default=0.0
    )
    cost_price = fields.Float(
        "Cost Price", required=True, digits="Product Price", default=0.0
    )
    price_subtotal = fields.Float("Subtotal", compute="_compute_amount")
    sale_order_templete_id = fields.Many2one("sale.order.template", string="Sale Order")
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )
    sequence = fields.Integer()

    @api.constrains("date")
    def check_date_duration_range(self):
        for rec in self:
            if rec.date and not (
                rec.sale_order_templete_id.arrival_date
                <= rec.date
                <= rec.sale_order_templete_id.return_date
            ):
                raise ValidationError(
                    _("The date should be in between the Arrival/Departure date!")
                )

    @api.onchange("date", "city_id")
    def _onchange_date_city(self):
        self.meal_id = False

    @api.onchange("meal_id")
    def _onchange_meal_id(self):
        self.meal_package_id = False
        if self.meal_id and self.date:
            contract = self.env["package.contract"].search(
                [
                    ("meal_id", "=", self.meal_id.id),
                    ("package_contract_type", "=", "meal"),
                    ("date_start", "<=", self.date),
                    ("date_end", ">=", self.date),
                    ("state", "=", "open"),
                ],
                limit=1,
            )
            self.contract_id = contract.id

    def _get_meal_description(self):
        if self.meal_id and self.meal_package_id:
            name = ""
            name += "Restaurant : {},{}".format(self.meal_id.name, self.city_id.name)
            name += "\n" + "Food Type: %s" % (self.meal_package_id.name)
            return name

    @api.onchange("meal_package_id")
    def onchange_restaurant_id(self):
        if self.meal_package_id:
            for rec in self:
                rec.name = rec._get_meal_description()
        if self.meal_id and self.contract_id:
            contract_line = self.contract_id.mapped("meal_contract_lines_ids").filtered(
                lambda a: a.meal_package_id.id == self.meal_package_id.id
            )
            self.update(
                {
                    "price_unit": (
                        contract_line.sales_price or self.meal_package_id.list_price
                    ),
                    "cost_price": (
                        contract_line.unit_price or self.meal_package_id.standard_price
                    ),
                }
            )


class PackageItinerary(models.Model):
    _inherit = "package.itinerary"

    meal_ids = fields.Many2many("template.meal.package.line", string="Restaurant")
