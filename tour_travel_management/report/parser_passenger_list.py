#  See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PassengerParser(models.AbstractModel):
    _name = "report.tour_travel_management.report_total_passenger_list"
    _description = "Passenger List Parser"

    @api.model
    def _get_report_values(self, docids, data=None):
        passenger_obj = self.env["wizzard.passenger.list"]
        docs = passenger_obj.browse(self.env.context.get("active_ids", []))
        if data.get("form"):
            passenger = (data.get("form")).get("passengers")
        if not data.get("form"):
            passenger = docids
        passenger = self.env["travellers.list"].browse(passenger)
        return {
            "doc_ids": [],
            "doc_model": "travellers.list",
            "docs": docs,
            "passenger": passenger,
        }
