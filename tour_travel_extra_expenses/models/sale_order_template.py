#  See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

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
        if context.get("guide_id"):
            services_line = self.env["guide.service.line"].search(
                [("guide_id", "=", context.get("guide_id"))]
            )
            services = services_line.mapped("service_id")
            args.append(["id", "in", services.ids])
        return super(ProductProduct, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class GuidePackageLine(models.Model):
    _name = "guide.package.line"
    _description = "Guide Package Line"

    name = fields.Text("Description", translate=True)
    date = fields.Date("Date")
    city_id = fields.Many2one("city.city", "City")
    guide_id = fields.Many2one("res.partner", "Guide")
    service_id = fields.Many2one("product.product", "Service")
    contact = fields.Char("Contact")
    price_unit = fields.Float("Rate", required=True, default=0.0)
    cost_price = fields.Float("Cost Price", required=True, default=0.0)
    sale_order_templete_id = fields.Many2one("sale.order.template", "Sale Order")
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )
    sequence = fields.Integer()

    @api.constrains("date")
    def _check_duration_range(self):
        for rec in self:
            if rec.date and not (
                rec.sale_order_templete_id.arrival_date
                <= rec.date
                <= rec.sale_order_templete_id.return_date
            ):
                raise ValidationError(
                    _("The date should be in between the Arrival/Departure date!")
                )

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            self.update(
                {
                    "name": self.service_id.display_name,
                    "price_unit": self.service_id.lst_price,
                    "cost_price": self.service_id.standard_price,
                }
            )


class ExtraTicketPackageLine(models.Model):
    _name = "extra.ticket.package.line"
    _description = "Extra Ticket Package Line"

    @api.depends("qty", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.qty * line.price_unit

    date = fields.Date("Date")
    ticket_id = fields.Many2one("product.product", "Ticket")
    supplier_id = fields.Many2one("res.partner", "Supplier")
    name = fields.Text("Description")
    qty = fields.Float("Qty", required=True, default=1.0)
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
    def _check_duration_range(self):
        for rec in self:
            if rec.date and not (
                rec.sale_order_templete_id.arrival_date
                <= rec.date
                <= rec.sale_order_templete_id.return_date
            ):
                raise ValidationError(
                    _("The date should be in between the Arrival/Departure date!")
                )

    @api.onchange("ticket_id")
    def _onchange_ticket_id(self):
        if self.ticket_id:
            self.update(
                {
                    "name": self.ticket_id.display_name,
                    "price_unit": self.ticket_id.list_price,
                    "cost_price": self.ticket_id.standard_price,
                }
            )


class SaleOrderTemplete(models.Model):
    _inherit = "sale.order.template"

    def get_cost_price(self):
        res = super(SaleOrderTemplete, self).get_cost_price()
        for order in self:
            extra_ticket_price = sum(
                [
                    line.cost_price * line.qty
                    for line in order.extra_ticket_package_line_ids
                    if line.qty != 0
                ]
            )
            guide_price = sum(
                [line.cost_price for line in order.guide_package_line_ids]
            )
        return res + guide_price + extra_ticket_price

    def get_sell_price(self):
        res = super(SaleOrderTemplete, self).get_sell_price()
        for order in self:
            extra_ticket_sell_price = sum(
                [
                    line.price_unit * line.qty
                    for line in order.extra_ticket_package_line_ids
                    if line.qty != 0
                ]
            )
            guide_sell_price = sum(
                [line.price_unit for line in order.guide_package_line_ids]
            )
        return res + guide_sell_price + extra_ticket_sell_price

    @api.depends(
        "guide_package_line_ids.cost_price", "extra_ticket_package_line_ids.cost_price"
    )
    def _compute_cost_per_person(self):
        for order in self:
            total_cost = self.get_cost_price()
            order.update({"cost_per_person": total_cost})

    @api.depends(
        "guide_package_line_ids.price_unit", "extra_ticket_package_line_ids.price_unit"
    )
    def _compute_sell_per_person(self):
        for order in self:
            total_sale_price = self.get_sell_price()
            order.update({"sell_per_person": total_sale_price})

    guide_package_line_ids = fields.One2many(
        "guide.package.line", "sale_order_templete_id", "Guide Package Lines"
    )
    extra_ticket_package_line_ids = fields.One2many(
        "extra.ticket.package.line",
        "sale_order_templete_id",
        "Extra Ticket Package Lines",
    )
    terms = fields.Html()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    extra_ticket_id = fields.Many2one("extra.ticket.package.line", "Extra Ticket")
    guide_id = fields.Many2one("guide.package.line", "Guide")
