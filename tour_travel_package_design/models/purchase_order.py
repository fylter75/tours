# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    arrival_date = fields.Date('Arrival Date', readonly=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)]})
    return_date = fields.Date('Departure Date', readonly=True,
                              states={'draft': [('readonly', False)],
                                      'sent': [('readonly', False)]})
    sale_order_id = fields.Many2one('sale.order',
                                    copy=False, string="Sale Order")
    meal_plan = fields.Char("Meal Plan", default="BB")
    budget = fields.Float("Budget")
    agreed_rate = fields.Float('Agreed Rate')

    @api.multi
    def action_rfq_send(self):
        """
        This function opens a window to compose an email, with the edi \
        purchase template message loaded by default
        """
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                temp_id = self.env.ref('purchase.email_template_edi_purchase')
            else:
                temp_id = self.env.ref(
                    'purchase.email_template_edi_purchase_done')
        except ValueError:
            temp_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail',
                'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        attach_obj = self.env['ir.attachment']

        pdf = self.env.ref(
            'tour_travel_package_design.qweb_booking_ref_report_id'
        ).render_qweb_pdf(
            [self.id])[0]
        result = base64.b64encode(pdf)

        pdf1 = self.env.ref(
            'tour_travel_package_design.qweb_po_report').render_qweb_pdf(
            [self.id])[0]
        result_book_ref = base64.b64encode(pdf1)

        pdf_rfq_quote = self.env.ref(
            'tour_travel_package_design.rfq_quote_report_id').render_qweb_pdf(
            [self.id])[0]
        result_rfq_quote = base64.b64encode(pdf_rfq_quote)

        attachment_ids = []
        if result:
            attach_data = {
                'name': 'Booking Reference with room list.pdf',
                'datas': result,
                'datas_fname': 'Booking Reference with room list.pdf',
                'res_model': 'ir.ui.view',
            }
            attach_id = attach_obj.create(attach_data)
            attachment_ids.append(attach_id.id)
        if result_book_ref:
            attach_data = {
                'name': 'Booking Reference.pdf',
                'datas': result_book_ref,
                'datas_fname': 'Booking Reference.pdf',
                'res_model': 'ir.ui.view',
            }
            attach_id = attach_obj.create(attach_data)
            attachment_ids.append(attach_id.id)
        if result_rfq_quote:
            attach_data = {
                'name': 'RFQ Quote.pdf',
                'datas': result_rfq_quote,
                'datas_fname': 'RFQ Quote.pdf',
                'res_model': 'ir.ui.view',
            }
            attach_id = attach_obj.create(attach_data)
            attachment_ids.append(attach_id.id)
        if attachment_ids:
            temp_id.write({'attachment_ids': [(6, 0, attachment_ids)]})

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(temp_id.id),
            'default_template_id': temp_id.id,
            'default_composition_mode': 'comment',
            'custom_layout':
            "purchase.mail_template_data_notification_email_purchase_order",
            'force_email': True
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class PurchaseOrderLine(models.Model):

    _inherit = 'purchase.order.line'

    from_date = fields.Date("From")
    to_date = fields.Date("To")
    product_uom = fields.Many2one('uom.uom', string='Product Unit \
                    of Measure', required=False)
    room_accupacy_id = fields.Many2one('room.room', "Room Accupacy")
    room_qty = fields.Integer('Room Qty')
