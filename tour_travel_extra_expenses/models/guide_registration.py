# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class GuideRegistration(models.Model):
    _inherit = "res.partner"
    _description = "Guide Registration"

    registration_type = fields.Selection(selection_add=[("guide", "Guide")])
    service_line_ids = fields.One2many("guide.service.line", "guide_id", "Services")


class GuideServiceLine(models.Model):
    _name = "guide.service.line"
    _rec_name = "service_id"
    _description = "Guide Service Line"

    guide_id = fields.Many2one("res.partner", "Guide")
    service_id = fields.Many2one("product.product", "Guide Service")
    unit_price = fields.Float("Unit Price")
    cost_price = fields.Float("Cost Price")

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            self.update(
                {
                    "unit_price": self.service_id.lst_price,
                    "cost_price": self.service_id.standard_price,
                }
            )
