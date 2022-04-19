# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SessionConfigSettings(models.Model):
    _name = "session.config"
    _description = "Session configuration settings"

    name = fields.Char("Name")
    start_time = fields.Float("Start Time")
    end_time = fields.Float("End Time")

    @api.constrains("start_time", "end_time")
    def _check_time_constraint(self):
        for record in self:
            if (
                record.start_time < 0.0
                or 24.0 < record.start_time
                or record.end_time < 0.0
                or 24.0 < record.end_time
            ):
                raise ValidationError(_("Start time or End time is wrong"))
            elif record.start_time > record.end_time:
                raise ValidationError(_("Start time must be smaller than End time"))
