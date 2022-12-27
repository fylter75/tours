#  See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PackageItinerary(models.Model):
    _name = "package.itinerary"
    _description = "Package Itinerary"

    sequence = fields.Char("Sequence")
    itinerary_date = fields.Date("Itinerary Date")
    days = fields.Char("Days")
    name = fields.Text("Description")
    sale_order_template_id = fields.Many2one(
        "sale.order.template", "Sale Order Template", ondelete="restrict"
    )
    event_time = fields.Float('Time')
    display_sctions = fields.Char("Display Sections")
    # description = fields.Char(string='Other Description')

class ProductCategory(models.Model):
    _inherit = "product.category"
    _description = "Product Category"

    type_travel_product = fields.Selection(
        [
            ("hotel", "Hotel"),
            ("transportation", "Transportation"),
            ("tickets", "Tickets"),
            ("ticketing", "Ticketing"),
            ("tour", "Tour"),
            ("meals", "Meals"),
            ("visa", "Visa"),
            ("guide", "Guide"),
            ("other", "Other"),
        ],
        string="Type",
    )


class CityCity(models.Model):
    _name = "city.city"
    _description = "City"

    name = fields.Char("City", required=True, index=True)
    state_id = fields.Many2one("res.country.state", "State", required=True, index=True)
    zip = fields.Char("Zip Code")


class GroupCosting(models.Model):
    _name = "group.costing.line"
    _description = "Group Costing Line"

    name = fields.Char("Description", required="True")
    sale_order_template_id = fields.Many2one(
        "sale.order.template", "Sale Order Template", ondelete="restrict"
    )
    number_of_adult = fields.Integer("Adult")
    number_of_children = fields.Integer("Children")
    sales_price = fields.Float("Sales Price")
    cost_price = fields.Float("Cost Price")

    @api.onchange("number_of_adult", "number_of_children")
    def _onchange_adult_children(self):
        for rec in self:
            rec.cost_price = (
                rec.number_of_adult + rec.number_of_children
            ) * rec.sale_order_template_id.cost_per_person
            rec.sales_price = (
                rec.number_of_adult + rec.number_of_children
            ) * rec.sale_order_template_id.sell_per_person
