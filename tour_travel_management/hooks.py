from odoo import SUPERUSER_ID, api


def test_uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tour_quotation = env.ref("sale.action_quotations_with_onboarding")
    tour_quotation.domain = []
    tour_order_to_invoice = env.ref("sale.action_orders_to_invoice")
    tour_order_to_invoice.domain = []
    tour_orders = env.ref("sale.action_orders")
    tour_orders.domain = []
