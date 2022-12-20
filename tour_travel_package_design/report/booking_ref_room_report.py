#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BookingRefRoom(models.AbstractModel):

    _name = 'report.tour_travel_package_design.qweb_booking_ref_room_report'
    _description = 'qweb booking ref room report'

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
        set the quantity of room, if rooms are already exist then add
        defined room otherwise it will take defined rooms.
        @param hotel_ids : list of records
        '''
        room_dict = {}
        for ho in hotel_ids:
            if ho.room_accupacy_id and ho.room_accupacy_id.room_selection in \
                    room_dict:
                room_dict[ho.room_accupacy_id.room_selection] += ho.room_qty
            elif ho.room_accupacy_id and ho.room_accupacy_id not in room_dict:
                room_dict[ho.room_accupacy_id.room_selection] = ho.room_qty
        return room_dict

    @api.model
    def _get_report_values(self, docids, data):
        report = self.env['ir.actions.report']._get_report_from_name(
            'tour_travel_package_design.qweb_booking_ref_room_report')
        po_ids = self.env['purchase.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': po_ids,
            'get_country': self.get_country,
            'get_room': self.get_room,
        }
