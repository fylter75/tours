#  See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FareType(models.Model):
    _name = "fare.type"
    _description = "Travel Fare type"

    name = fields.Char("Fare Type")


class TicketPackageLine(models.Model):
    _name = "ticket.package.line"
    _description = "Ticket"

    @api.depends("unit_price", "qty")
    def _compute_subtotal(self):
        for line in self:
            price = line.unit_price * line.qty
            line.update({"price_subtotal": price})

    name = fields.Text("Description", translate=True)
    product_id = fields.Many2one("product.product", "Ticket", ondelete="restrict")
    source_id = fields.Many2one("city.city", "Source")
    destination_id = fields.Many2one("city.city", "Destination")
    issue_date = fields.Date("Issue Date")
    fare_type_id = fields.Many2one("fare.type", "Fare Type", ondelete="restrict")
    ticket_no = fields.Char("Ticket No")
    qty = fields.Integer("Qty", default=1)
    cost_price = fields.Float("Cost Price")
    unit_price = fields.Float("Unit Price")
    price_subtotal = fields.Float("Subtotal", compute="_compute_subtotal")
    sale_order_templete_id = fields.Many2one(
        "sale.order.template", string="Sale Order", ondelete="cascade"
    )
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Technical field for UX purpose.",
    )
    sequence = fields.Integer()

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.update(
                {
                    "unit_price": self.product_id.list_price,
                    "cost_price": self.product_id.standard_price,
                }
            )

    def _get_ticket_description(self):
        if self.product_id and self.fare_type_id:
            name = ""
            name += "Ticket type : %s " % (self.product_id.name)
            name += "Journey : {} -> {}".format(
                self.source_id.name, self.destination_id.name,
            )
            name += "\n" + "Fare Type: %s" % (self.fare_type_id.name)
            return name

    @api.onchange("fare_type_id")
    def _onchange_fare_type_id(self):
        if self.fare_type_id:
            for rec in self:
                rec.name = rec._get_ticket_description()
