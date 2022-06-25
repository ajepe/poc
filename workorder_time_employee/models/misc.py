# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
import pytz
from pytz import timezone, utc

class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    duration = fields.Float('Duration', compute='_compute_duration', inverse='compute_duration_inverse', store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee")

    def compute_duration_inverse(self):
        for blocktime in self:
            if blocktime.date_start and blocktime.date_end:
                d2 = fields.Datetime.from_string(blocktime.date_start)
                blocktime.date_end = fields.Datetime.to_string(d2 + timedelta(hours=blocktime.duration))