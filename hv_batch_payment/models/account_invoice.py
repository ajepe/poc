# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    payment_amount = fields.Float(string='Payment Amount', default=0.0)

    def action_register_batch_payment(self):
        return {
            'name': _('Register Batch Payment'),
            'res_model': 'wizard.payment.batch',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }