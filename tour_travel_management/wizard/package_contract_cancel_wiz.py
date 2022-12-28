from odoo import fields, models


class PackageContractCancel(models.TransientModel):
    _name = "package.contract.cancel.wiz"
    _description = "Package Contract Cancel Wiz"

    cancel_reason_id = fields.Many2one(
        "package.contract.cancel", "Cancel Reason", required=True
    )

    def action_cancel_reason_apply(self):
        contract = self.env["package.contract"].browse(
            self.env.context.get("active_ids")
        )
        contract.update(
            {"cancel_reason_id": self.cancel_reason_id.id, "state": "cancel"}
        )
