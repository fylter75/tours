from odoo import fields, models


class TravellingSeason(models.Model):
    _name = "travelling.season"
    _description = "Travelling Session"

    name = fields.Char("Season")
