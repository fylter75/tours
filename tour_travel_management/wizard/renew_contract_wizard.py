#  See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WizardRenewcontract(models.TransientModel):
    _name = "renew.contract"
    _description = "Renew contract"

    date_start = fields.Date(string="Start Date", help="Contract start date")
    date_end = fields.Date(string="End Date", help="Contract end date")

    def renew_contract(self):
        if self._context.get("active_id"):
            for rec in self:
                contract_id = self.env["package.contract"].browse(
                    self._context.get("active_id")
                )
                contract_id.write(
                    {
                        "date_start": rec.date_start,
                        "date_end": rec.date_end,
                        "state": "draft",
                    }
                )
