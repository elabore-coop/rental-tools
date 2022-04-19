# -*- coding: utf-8 -*-

from odoo import models, fields


class RentalProductOperation(models.Model):
    _name = "rental.product.operation"
    _description = "product Products Operation"

    name = fields.Char(string="Operation Types Name", required=True, translate=True)
    color = fields.Integer(string="Color")
    rental_move_type = fields.Selection(
        [("outgoing", "Customers"), ("incoming", "Return"), ("internal", "Internal")],
        string="Types of Operation",
        required=True,
        default="outgoing",
    )
    source_location = fields.Many2one("stock.location", string="Source Location")
    destination_location = fields.Many2one(
        "stock.location", string="Destination Location"
    )
    location_id = fields.Many2one("stock.location", string="Location")
    state = fields.Selection(
        [
            ("ready", "Ready"),
            ("on_rent", "On Rent"),
            ("service", "Service"),
            ("done", "Done"),
        ]
    )
    count_operation_ready = fields.Integer(compute="_compute_operation_count")
    count_operation_on_rent = fields.Integer(compute="_compute_operation_count")
    count_operation_service = fields.Integer(compute="_compute_operation_count")
    operation_type_id = fields.Many2one(
        "rental.product.operation", string="Operation Type"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )

    rental_move_type = fields.Selection(
        [("outgoing", "Customers"), ("incoming", "Return"), ("internal", "Internal")],
        string="Types of Operation",
        required=True,
        default="internal",
    )

    def _compute_operation_count(self):
        for each in self:
            ready_state = self.env["stock.picking"].search_count(
                [
                    ("state", "in", ["draft"]),
                    ("location_id", "=", each.location_id.id),
                    ("is_rental", "=", True),
                ]
            )
            each.count_operation_ready = ready_state
            on_rent_state = self.env["stock.picking"].search_count(
                [
                    ("location_id", "=", each.location_id.id),
                    ("state", "=", "confirmed"),
                    ("is_rental", "=", True),
                ]
            )
            each.count_operation_on_rent = on_rent_state
            service_state = self.env["stock.picking"].search_count(
                [
                    ("state", "=", "assigned"),
                    ("location_id", "=", each.location_id.id),
                    ("is_rental", "=", True),
                ]
            )
            each.count_operation_service = service_state

    def get_action_operation(self):
        if self.rental_move_type == "outgoing":
            state = ["draft"]
        elif self.rental_move_type == "incoming":
            state = ["confirmed"]
        elif self.rental_move_type == "internal":
            state = ["assigned"]
        action_id = self.env.ref(
            "product_rental_bookings.action_rental_product_move"
        ).read()[0]
        action_id["context"] = {"default_rental_move_type": self.rental_move_type}
        action_id["domain"] = [
            ("state", "in", state),
            ("rental_move_type", "=", self.rental_move_type),
            ("location_id", "in", self.location_id.ids),
        ]
        return action_id
