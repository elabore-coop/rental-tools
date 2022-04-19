# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    rental_order_id = fields.Many2one("rental.product.order", string="Rental ref   ")
    interval_type = fields.Selection(
        [("days", "Day"), ("weeks", "Week"), ("months", "Month")],
        string="Interval Type",
    )
    interval_number = fields.Integer(string="Interval Number", readonly=1)
    is_recurring = fields.Boolean(string="Recurring Invoice", default=False)
    contract_id = fields.Many2one("rental.product.contract", string="Contract")
    is_hours = fields.Boolean(string="Hours")
    is_days = fields.Boolean(string="Days")

    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != "open")
        if to_open_invoices.filtered(lambda inv: inv.state != "draft"):
            raise UserError(
                _("Invoice must be in draft state in order to validate it.")
            )
        if to_open_invoices.filtered(lambda inv: inv.amount_total < 0):
            raise UserError(
                _(
                    "You cannot validate an invoice with a negative total amount. You should create a credit note instead."
                )
            )
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        if (
            self.interval_number > 0
            and self.is_recuuring == False
            and self.date_due >= datetime.now().strftime("%y-%m-%d-%H-%M")
        ):
            self.is_recuuring = True
            sub_name = (
                str(self.number)
                + str("-" + self.interval_type if self.interval_type else "")
                + "-"
                + datetime.now().strftime("%Y-%m-%d")
            )
            model_id = self.env["ir.model"].search([("model", "=", self._name)])

            subscription_document_id = self.env["subscription.document"].search(
                [("name", "=", "Account Invoice"), ("model", "=", model_id.id)], limit=1
            )
            if not subscription_document_id:
                subscription_document_id = self.env["subscription.document"].create(
                    {"name": "Account Invoice", "model": model_id.id}
                )
            subscription_doc_source = (
                str(subscription_document_id.model.model) + "," + str(self.id)
            )
            subscription_id = self.env["subscription.subscription"].create(
                {
                    "name": sub_name,
                    "partner_id": self.partner_id.id,
                    "interval_number": self.interval_number,
                    "interval_type": self.interval_type,
                    "doc_source": subscription_doc_source,
                }
            )
            subscription_id.set_process()
        return to_open_invoices.action_invoice_open()


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    product_id = fields.Many2one("product.product", string="Product ID")
    enter_hour = fields.Float(string="Hour")
    enter_days = fields.Float(string="Days")

    def _get_computed_price_unit(self):
        self.ensure_one()

        if not self.product_id:
            return self.price_unit
        elif self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            price_unit = self.product_id.lst_price
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            price_unit = self.product_id.standard_price
        else:
            return self.price_unit

        if self.product_uom_id != self.product_id.uom_id:
            price_unit = self.product_id.uom_id._compute_price(
                price_unit, self.product_uom_id
            )

        if self.enter_days:
            price_unit = price_unit * self.enter_days
        elif self.enter_hour:
            price_unit = price_unit * self.enter_hour

        return price_unit
