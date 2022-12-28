from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_discount_id = fields.Many2one(
        "product.product",
        string="Package Discount",
        required=True,
        config_parameter="tour_travel_management.product_discount_id",
        default=lambda self: self.env.ref(
            "tour_travel_management.package_discount").id,
    )
    product_extra_bed_id = fields.Many2one(
        "product.product",
        string="Extra Bed",
        required=True,
        config_parameter="tour_travel_management.product_extra_bed_id",
        default=lambda self: self.env.ref(
            "tour_travel_management.package_extra_bed"
        ).id,
    )
