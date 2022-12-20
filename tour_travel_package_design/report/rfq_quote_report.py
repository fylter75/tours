#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class RfqQuote(models.AbstractModel):

    _name = 'report.tour_travel_package_design.qweb_rfq_quote_report'
    _description = 'qweb rfq quote report'

    @api.multi
    def get_country(self, passenger_ids):
        '''
        set the nationality
        @param pessanger_ids : list of records
        '''
        con = []
        for pas in passenger_ids:
            if pas.country_id:
                con.append(pas.country_id.name)
        nationality = ''
        for coun in list(set(con)):
            nationality += coun + ', '
        return nationality

    @api.multi
    def get_room(self, hotel_ids):
        '''
        count the room's quantity.
        @param hotel_ids : list of records
        '''
        room = sum([ho.room_qty for ho in hotel_ids if ho.room_qty])
        return room

    @api.model
    def _get_report_values(self, docids, data):
        report = self.env['ir.actions.report']._get_report_from_name(
            'tour_travel_package_design.qweb_rfq_quote_report')
        po_ids = self.env['purchase.order'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': po_ids,
            'get_country': self.get_country,
            'get_room': self.get_room,
        }
