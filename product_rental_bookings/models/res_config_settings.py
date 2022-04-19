# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enabled_day_rent = fields.Boolean(string="Day Rent")
    enabled_hour_rent = fields.Boolean(string="Hour Rent")
    enabled_session_rent = fields.Boolean(string="Session Rent")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env["ir.config_parameter"].sudo().get_param
        res.update(
            enabled_day_rent=get_param("enabled_day_rent"),
            enabled_hour_rent=get_param("enabled_hour_rent"),
            enabled_session_rent=get_param("enabled_session_rent"),
        )
        return res

    def set_values(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "enabled_day_rent", self.enabled_day_rent
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "enabled_hour_rent", self.enabled_hour_rent
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "enabled_session_rent", self.enabled_session_rent
        )
        res = super(ResConfigSettings, self).set_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        ICPSudo.set_param(
            "product_rental_bookings.enabled_day_rent", self.enabled_day_rent
        )
        ICPSudo.set_param(
            "product_rental_bookings.enabled_day_rent", self.enabled_hour_rent
        )
        ICPSudo.set_param(
            "product_rental_bookings.enabled_day_rent", self.enabled_session_rent
        )
        return res
