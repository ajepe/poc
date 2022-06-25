# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic Account")

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveLine, self).default_get(fields)
        if self._context.get('move_type') and self._context.get('move_type') in ['out_invoice','in_invoice']:
            res['analytic_account_id'] = self.move_id.partner_id.analytic_account_id and  self.move_id.partner_id.analytic_account_id.id or False
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        super(AccountMoveLine,self)._onchange_product_id()
        for line in self:
            if line.move_id.move_type in ['out_invoice','in_invoice']:
                line.analytic_account_id = line.move_id.partner_id.analytic_account_id and  line.move_id.partner_id.analytic_account_id.id or False