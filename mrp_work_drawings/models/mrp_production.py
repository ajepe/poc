# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pdf_manual = fields.Binary('Work Drawings')
    filename = fields.Char('Filename')

    @api.onchange('pdf_manual')
    def set_drawings(self):
        if self.pdf_manual:
            for wo in self.workorder_ids:
                new_draw = self.env['workorder.drawings'].create({'name': self.filename, 'pdf_manual': self.pdf_manual})
                new_draw.work_order_id = wo._origin.id

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    drawings_ids = fields.One2many("workorder.drawings", "work_order_id", string="Drawings")

class WorkorderDrawing(models.Model):
    _name = 'workorder.drawings'
    _rec_name = 'name'

    name = fields.Char('Filename')
    pdf_manual = fields.Binary('Drawing')
    work_order_id = fields.Many2one("mrp.workorder", string="Workorder")