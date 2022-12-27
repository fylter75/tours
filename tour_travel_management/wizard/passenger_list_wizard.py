#  See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PassengerList(models.TransientModel):
    _name = "wizzard.passenger.list"
    _description = "Passenger List"

    package_id = fields.Many2one(
        "sale.order.template", required=True, string="Package",
    )

    def package_passenger_list(self):
        if self.package_id:
            passenger = []
            data = {}
            registrations = self.env["sale.order"].search(
                [
                    ("sale_order_template_id", "=", self.package_id.id),
                    ("state", "=", "sale"),
                ]
            )
            for registration in registrations:
                for passengers in registration.passenger_ids:
                    passenger.append(passengers.id)
            data["passengers"] = passenger
            data["package_id"] = self.package_id
            datas = {
                "ids": [],
                "model": "travellers.list",
                "form": data,
            }
            return self.env.ref(
                "tour_travel_management.action_total_passenger_list"
            ).report_action([], data=datas)
