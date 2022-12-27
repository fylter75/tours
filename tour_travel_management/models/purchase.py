#  See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    package_id = fields.Many2one("sale.order.template", "Package")
