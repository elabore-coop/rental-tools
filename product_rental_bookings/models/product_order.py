# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime

import pytz
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference_prefix(self, values):
        prefix = super(PaymentTransaction, self)._compute_reference_prefix(values)
        if not prefix and values:
            prefix = "Rental Order"
        return prefix

    def render_rental_button(self, order, submit_txt=None, render_values=None):
        values = {
            "partner_id": order.partner_shipping_id.id or order.partner_invoice_id.id,
            "billing_partner_id": order.partner_invoice_id.id,
            "type": "form_save",
        }
        if render_values:
            values.update(render_values)
        self._log_payment_transaction_sent()
        return (
            self.acquirer_id.with_context(
                submit_class="btn btn-primary", submit_txt=submit_txt or _("Pay Now")
            )
            .sudo()
            .render(
                self.reference,
                order.total_amount,
                order.currency_id.id,
                values=values,
            )
        )


class RentalProductOrder(models.Model):
    _name = "rental.product.order"
    _description = "product Product Order"
    _rec_name = "res_number"

    def _default_price_list(self):
        return (
            self.env["product.pricelist"]
            .search(
                [
                    ("company_id", "in", (False, self.env.company.id)),
                    ("currency_id", "=", self.env.company.currency_id.id),
                ],
                limit=1,
            )
            .id
        )

    res_number = fields.Char(string="Order number", readonly=True, default="New")
    product_name = fields.Many2one("product.product", string="Product Name")
    from_date = fields.Datetime(string="From Date")
    date_order = fields.Datetime(string="Date From")
    to_date = fields.Datetime(string="To Date")
    start_date = fields.Char(string="start Date")
    end_date = fields.Char(string="end Date")
    customer_name = fields.Many2one("res.partner", string="Customer Name")
    book_date = fields.Datetime(string="Booking Date", default=datetime.now())
    account_payment_term = fields.Many2one(
        "account.payment.term", string="Payment Term", required=True, default=1
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("cancel", "Cancel"),
            ("close", "Close"),
        ],
        default="draft",
    )
    is_invoice = fields.Boolean(string="invoice")
    rental_product_ids = fields.One2many(
        "product.product", "product_registration_id", string="Product"
    )
    is_agreement = fields.Boolean(string="Contracts Require?", default=True)
    product_order_lines_ids = fields.One2many(
        "product.order.line", "product_order_id", string="Order Line "
    )
    invoice_count = fields.Integer(compute="_invoice_total", string="Total Invoiced")
    contract_count = fields.Integer(compute="_contract_total", string="Total Contract")
    picking_count = fields.Integer(compute="_picking_total", string="Total Invoiced ")
    stock_picking_ids = fields.One2many(
        "stock.picking", "product_order_rel_id", string="Picking Id"
    )
    invoice_ids = fields.One2many(
        "account.move", "rental_order_id", string="Invoice Id"
    )
    contract_ids = fields.One2many(
        "rental.product.contract", "rental_id", string="Contract Id"
    )
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Pricelist", default=_default_price_list
    )  # _default_pricelist
    extra_charges = fields.Monetary(string="Extra Charges", readonly=True)
    total_amount = fields.Monetary(
        string="Total Amount", compute="_compute_amount", store=True
    )
    taxes = fields.Float(string="Taxes", compute="_compute_amount", store=True)
    untaxed_amount = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amount", store=True
    )
    amount_untaxed = fields.Monetary(string="Untaxed Amount 1")

    user_id = fields.Many2one(
        "res.users", string="Dealer", default=lambda self: self.env.user
    )
    terms_condition = fields.Text(string="Terms And Condition")
    invoice_status = fields.Char(compute="get_invoice_status", string="Invoice Status")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.user.company_id,
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    count = fields.Integer(
        string="Count", compute="_compute_count", store=True, invisible=True
    )
    is_true = fields.Boolean(string="True")
    partner_shipping_id = fields.Many2one(
        "res.partner", related="customer_name", string="Delivery Address"
    )
    partner_invoice_id = fields.Many2one(
        "res.partner", "Invoicing Address", related="customer_name"
    )
    return_date = fields.Datetime("Return Date")
    location_id = fields.Many2one("stock.location", string="Location")
    is_hours = fields.Boolean(string="Hours")
    is_days = fields.Boolean(string="Days")

    def _create_payment_transaction(self, vals):
        """Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current sales orders fields (e.g. the partner or the currency).
        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        """
        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = int(vals.get("acquirer_id"))
        acquirer = False
        payment_token_id = vals.get("payment_token_id")
        acquirer = self.env["payment.acquirer"].browse(acquirer_id)
        partner = self.env["res.partner"].browse(vals.get("partner_id"))
        if payment_token_id and acquirer_id:
            payment_token = (
                self.env["payment.token"].sudo().browse(int(payment_token_id))
            )
            if payment_token and payment_token.acquirer_id != acquirer:
                raise ValidationError(
                    _("Invalid token found! Token acquirer %s != %s")
                    % (payment_token.acquirer_id.name, acquirer.name)
                )
            if payment_token and payment_token.partner_id != partner:
                raise ValidationError(
                    _("Invalid token found! Token partner %s != %s")
                    % (payment_token.partner_id.name, partner.name)
                )
            else:
                acquirer = payment_token.acquirer_id
        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise ValidationError(
                _("A payment acquirer is required to create a transaction.")
            )
        if not acquirer:
            acquirer = self.env["payment.acquirer"].browse(acquirer_id)
        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise ValidationError(
                _("A journal must be specified of the acquirer %s." % acquirer.name)
            )
        if not acquirer_id and acquirer:
            vals["acquirer_id"] = acquirer.id
        vals.update(
            {
                "date": datetime.now(),
                "amount": vals.get("amount"),
                "currency_id": vals.get("currency_id"),
                "partner_id": vals.get("partner_id"),
            }
        )
        transaction = self.env["payment.transaction"].create(vals)
        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()
        return transaction

    @api.depends("customer_name")
    def _compute_count(self):
        self.ensure_one()
        self.count = len(self.search([("customer_name", "=", self.customer_name.id)]))

    @api.depends("invoice_status")
    def get_invoice_status(self):
        for record in self:
            record.invoice_status = ""
            for invoice in record.invoice_ids:
                record.invoice_status = invoice.state

    @api.onchange("customer_name")
    def onchange_customer(self):
        self.account_payment_term = self.customer_name.property_payment_term_id.id

    @api.depends("stock_picking_ids")
    def _picking_total(self):
        for order in self:
            order.picking_count = len(order.stock_picking_ids)

    @api.depends("invoice_ids")
    def _invoice_total(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    def convert_TZ_UTC(self, TZ_datetime):
        fmt = "%Y-%m-%d %H:%M:%S"
        # Current time in UTC
        now_utc = datetime.now(pytz.timezone("UTC"))
        # Convert to current user time zone
        now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
        UTC_OFFSET_TIMEDELTA = datetime.strptime(
            now_utc.strftime(fmt), fmt
        ) - datetime.strptime(now_timezone.strftime(fmt), fmt)
        local_datetime = datetime.strptime(TZ_datetime, fmt)
        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
        return result_utc_datetime.strftime(fmt)

    def action_view_order_invoices(self):
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        invoices = self.mapped("invoice_ids")
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif invoices:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.id
        return action

    @api.depends("contract_ids")
    def _contract_total(self):
        for contract in self:
            contract.contract_count = len(contract.contract_ids)

    def action_view_order_contract(self):
        action = self.env.ref(
            "product_rental_bookings.action_rental_contract_view_tree"
        ).read()[0]
        contracts = self.mapped("contract_ids")
        if len(contracts) > 1:
            action["domain"] = [("id", "in", contracts.ids)]
        elif contracts:
            action["views"] = [
                (
                    self.env.ref(
                        "product_rental_bookings.rental_product_contract_form"
                    ).id,
                    "form",
                )
            ]
            action["res_id"] = contracts.id
        return action

    @api.onchange("customer_name")
    def customer_pricelist(self):
        values = {
            "pricelist_id": self.customer_name.property_product_pricelist
            and self.customer_name.property_product_pricelist.id
            or False,
        }
        self.update(values)

    @api.model
    def create(self, vals):
        product_order_line = []
        if vals.get("is_true"):
            for order_line in vals.get("product_order_lines_ids"):
                if order_line[2] and order_line[0] != 0:
                    product_order_line.append([0, False, order_line[2]])
                elif order_line[2] and order_line[0] == 0:
                    product_order_line.append(order_line)
            vals.update({"product_order_lines_ids": product_order_line})
        sequence = self.env["ir.sequence"].next_by_code("product_registration") or _(
            "Product Register"
        )
        vals.update({"res_number": sequence})
        res = super(RentalProductOrder, self).create(vals)
        from_date, to_date = self.start_end_date_global(res.from_date, res.to_date)
        res.start_date = from_date
        res.end_date = to_date
        return res

    @api.depends("product_order_lines_ids", "customer_name")
    def _compute_amount(self):
        """
        Compute the total amounts of the RO.
        """
        for order in self:
            untaxed_amount = 0.0
            taxes = 0.0
            for line in order.product_order_lines_ids:
                untaxed_amount += line.sub_total
                taxes += line.price_tax
            if order.pricelist_id:
                order.update(
                    {
                        "untaxed_amount": order.pricelist_id.currency_id.round(
                            untaxed_amount
                        ),
                        "taxes": order.pricelist_id.currency_id.round(taxes),
                        "total_amount": untaxed_amount + taxes + order.extra_charges,
                    }
                )
            else:
                order.update(
                    {
                        "untaxed_amount": untaxed_amount,
                        "taxes": taxes,
                        "total_amount": untaxed_amount + taxes + order.extra_charges,
                    }
                )

    def book(self):
        self.state = "book"

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return picking_type[:1].id

    def confirm(self):
        product_order_id = []
        move_ids_without_package = []
        for each in self.product_order_lines_ids:
            product_order_id.append((0, 0, {"product_id": each.product_id.id}))
            move_ids_without_package.append(
                (
                    0,
                    0,
                    {
                        "product_id": each.product_id.id,
                        "product_uom_qty": each.qty_needed,
                        "product_uom": each.product_id.uom_id.id,
                        "location_id": self.location_id.id
                        or each.product_id.location_id.id,
                        "location_dest_id": self.env.ref(
                            "stock.stock_location_customers"
                        ).id,
                        "name": each.product_id.name,
                        "company_id": self.company_id.id,
                    },
                )
            )

        stock_picking_id = self.env["stock.picking"].create(
            {
                "partner_id": self.customer_name.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "rental_move_type": "outgoing",
                "picking_type_id": self._get_picking_type(self.company_id.id),
                "product_order_rel_id": self.id,
                "is_rental": True,
                "origin": self.res_number,
                "move_ids_without_package": move_ids_without_package,
            }
        )
        self.state = "confirm"
        if self.is_agreement:
            rental_product_contract_obj = self.env["rental.product.contract"]
            product_order_id = []
            for each in self.product_order_lines_ids:
                product_order_id.append(
                    (
                        0,
                        0,
                        {
                            "product_id": each.product_id.id or "",
                            "price_based": each.price_based or "",
                            "enter_days": each.enter_days or "",
                            "enter_hour": each.enter_hour or "",
                            "price": each.price or "",
                            "qty_needed": each.qty_needed,
                            "sub_total": each.sub_total or "",
                            "tax_id": [(6, 0, each.tax_id.ids)],
                        },
                    )
                )
            self.state = "confirm"
            view_id = self.env.ref(
                "product_rental_bookings.rental_product_contract_form"
            )
            contract = rental_product_contract_obj.create(
                {
                    "partner_id": self.customer_name.id,
                    "from_date": self.from_date,
                    "to_date": self.to_date,
                    "total_amount": self.total_amount,
                    "rental_id": self.id,
                    "product_contract_lines_ids": product_order_id,
                    "cost_frequency": "no",
                    "contract_date": self.book_date,
                    "account_payment_term": self.account_payment_term.id,
                    "contractor_id": self.user_id.id,
                    "origin": self.res_number,
                    "cost": 12,
                    "is_hours": self.is_hours,
                    "is_days": self.is_days,
                    "picking_id": stock_picking_id.id,
                    "company_id": self.company_id.id,
                    "name": "New",
                }
            )
            return {
                "name": _("product Contract"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "rental.product.contract",
                "res_id": contract.id,
                "view_id": view_id.id,
            }
        self.state = "confirm"

    def action_view_invoice(self):
        invoices = self.mapped("invoice_ids")
        action = self.env.ref("account.action_invoice_tree1").read()[0]
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            action["views"] = [(self.env.ref("account.move_form").id, "form")]
            action["res_id"] = invoices.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def action_view_stock_pickings(self):
        pickings = self.mapped("stock_picking_ids")
        return {
            "name": "Pickings",
            "view_mode": "tree,form",
            "res_model": "stock.picking",
            "domain": [("id", "in", pickings.ids)],
            "res_id": self.id,
            "type": "ir.actions.act_window",
        }

    def cancel(self):
        inv_obj = self.env["account.move"]
        order_id = self.env["product.order.line"].browse(int(self.id)).product_order_id
        self = order_id
        for contract in order_id.contract_ids:
            for cancel_policy in contract.cancel_policy_ids:
                if cancel_policy.from_date and cancel_policy.to_date:
                    if (
                        date.today() >= cancel_policy.from_date
                        and date.today() <= cancel_policy.to_date
                    ):
                        invoice_browse = (
                            self.env["account.move"]
                            .sudo()
                            .search(
                                [
                                    ("contract_id", "=", contract.id),
                                    ("type", "=", "out_invoice"),
                                ]
                            )
                        )
                        for each_invoice in invoice_browse:
                            if each_invoice.state == "draft":
                                invoice_line_data = []
                                invoice_line_data.append(
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": self.product_name.id,
                                            "name": "Cancel Policy " + self.res_number,
                                            "account_id": self.customer_name.property_account_receivable_id.id,
                                            "price_unit": (
                                                contract.total_amount
                                                * cancel_policy.policy_charged
                                            )
                                            / 100,
                                            "quantity": 1,
                                        },
                                    )
                                )
                                invoice = inv_obj.create(
                                    {
                                        "name": self.res_number,
                                        "origin": self.res_number,
                                        "partner_id": self.customer_name.id,
                                        "type": "out_invoice",
                                        "date_invoice": date.today(),
                                        "reference": False,
                                        "account_id": self.customer_name.property_account_receivable_id.id,
                                        "invoice_line_ids": invoice_line_data,
                                    }
                                )

                            elif each_invoice.state == "paid":
                                invoice_line_data = []
                                invoice_line_data.append(
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": self.product_name.id,
                                            "name": "Cancel Policy " + self.res_number,
                                            "account_id": self.customer_name.property_account_receivable_id.id,
                                            "price_unit": each_invoice.total_amount
                                            - (
                                                (
                                                    contract.total_amount
                                                    * cancel_policy.policy_charged
                                                )
                                                / 100
                                            ),
                                            "quantity": 1,
                                        },
                                    )
                                )
                                invoice = inv_obj.create(
                                    {
                                        "name": self.res_number,
                                        "origin": self.res_number,
                                        "partner_id": self.customer_name.id,
                                        "type": "in_refund",
                                        "date_invoice": date.today(),
                                        "reference": False,
                                        "account_id": self.customer_name.property_account_receivable_id.id,
                                        "invoice_line_ids": invoice_line_data,
                                    }
                                )

                if not cancel_policy.to_date:
                    if date.today() >= cancel_policy.from_date:
                        invoice_browse = self.env["account.move"].search(
                            [
                                ("contract_id", "=", contract.id),
                                ("type", "=", "out_invoice"),
                            ]
                        )
                        for each_invoice in invoice_browse:
                            if each_invoice.state == "draft":
                                each_invoice.state = "paid"
        self.state = "cancel"

    def send_product_quote(self):
        """
        This is Email for send quotation product order inquiry
        """
        self.ensure_one()
        ir_model_data = self.env["ir.model.data"]
        try:
            template_id = ir_model_data.get_object_reference(
                "product_rental_bookings", "email_template_product_rental"
            )[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                "mail", "email_compose_message_wizard_form"
            )[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            "default_model": "rental.product.order",
            "default_res_id": self.ids[0],
            "default_use_template": bool(template_id),
            "default_template_id": template_id,
            "mark_so_as_sent": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def close(self):
        view_id = self.env.ref("rental_product_rental")
        return {
            "name": "product Service",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "wizard.product.service",
            "view_id": view_id.id,
            "target": "new",
        }

    @api.model
    def start_end_date_global(self, start, end):
        tz = pytz.utc
        current_time = datetime.now(tz)
        hour_tz = int(str(current_time)[-5:][:2])
        min_tz = int(str(current_time)[-5:][3:])
        sign = str(current_time)[-6][:1]
        sdate = str(start)
        edate = str(end)

        if sign == "+":
            start_date = (
                datetime.strptime(sdate, "%Y-%m-%d %H:%M:%S")
                + timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_date = (
                datetime.strptime(edate, "%Y-%m-%d %H:%M:%S")
                + timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")

        if sign == "-":
            start_date = (
                datetime.strptime(sdate, "%Y-%m-%d %H:%M:%S")
                - timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_date = (
                datetime.strptime(edate, "%Y-%m-%d %H:%M:%S")
                - timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
        return start_date, end_date

    @api.model
    def start_and_end_date_global(self, start, end):
        tz = pytz.timezone(self.env.user.tz) or "UTC"
        current_time = datetime.now(tz)
        hour_tz = int(str(current_time)[-5:][:2])
        min_tz = int(str(current_time)[-5:][3:])
        sign = str(current_time)[-6][:1]
        sdate = str(start)
        edate = str(end)

        if sign == "-":
            start_date = (
                datetime.strptime(sdate.split(".")[0], "%Y-%m-%d %H:%M:%S")
                + timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_date = (
                datetime.strptime(edate.split(".")[0], "%Y-%m-%d %H:%M:%S")
                + timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")

        if sign == "+":
            start_date = (
                datetime.strptime(sdate.split(".")[0], "%Y-%m-%d %H:%M:%S")
                - timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
            end_date = (
                datetime.strptime(edate.split(".")[0], "%Y-%m-%d %H:%M:%S")
                - timedelta(hours=hour_tz, minutes=min_tz)
            ).strftime("%Y-%m-%d %H:%M:%S")
        return start_date, end_date

    @api.model
    def utc_to_tz(self, start, end):
        start_date = pytz.utc.localize(
            datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        ).astimezone(pytz.timezone(self.env.user.tz))

        end_date = pytz.utc.localize(
            datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        ).astimezone(pytz.timezone(self.env.user.tz))

        return start_date, end_date

    @api.model
    def get_booking_data(self, model_id):
        resourcelist = []
        eventlist = []
        id_list = []
        product_booking = self.env["rental.product.order"].search(
            [("state", "in", ["confirm"])]
        )
        categ_ids = self.env["product.category"].search(
            [("parent_id", "child_of", int(model_id))]
        )
        for data in product_booking:
            if data.product_order_lines_ids and data.from_date.date() >= date.today():
                for line in data.product_order_lines_ids:
                    if (
                        line.product_id.categ_id.id in categ_ids.ids
                        and line.product_id.id not in id_list
                    ):
                        resourcelist.append(
                            {
                                "id": line.product_id.id,
                                "building": line.product_id.categ_id.name,
                                "title": line.product_id.name,
                                "type": line.product_id.categ_id.id or False,
                                "product_id": line.product_id.id,
                            }
                        )
                        id_list.append(line.product_id.id)
                    if line.product_id.categ_id.id in categ_ids.ids:
                        if data.start_date and data.end_date:
                            start_date, end_date = self.utc_to_tz(
                                data.start_date, data.end_date
                            )
                            start = (
                                str(start_date.date()) + "T" + str(start_date.time())
                            )
                            end = str(end_date.date()) + "T" + str(end_date.time())
                        else:
                            start_date, end_date = self.utc_to_tz(
                                data.start_date, data.end_date
                            )
                            start = (
                                str(start_date.date()) + "T" + str(start_date.time())
                            )
                            end = str(end_date.date()) + "T" + str(end_date.time())
                        eventlist.append(
                            {
                                "id": line.id,
                                "line_id": line.id,
                                "resourceId": line.product_id.id,
                                "start": start,
                                "end": end,
                                "title": data.res_number,
                                "type": model_id or False,
                                "product_id": line.product_id.id,
                            }
                        )
        product_model = self.env["product.product"].search([("is_rental", "=", True)])
        for product in product_model:
            if product.categ_id.id in categ_ids.ids and product.id not in id_list:
                id_list.append(product.id)
                resourcelist.append(
                    {
                        "id": product.id,
                        "building": product.categ_id.name,
                        "title": product.name,
                        "type": product.categ_id.id or False,
                        "product_id": product.id,
                    }
                )
        if not resourcelist:
            eventlist = []
        return [resourcelist, eventlist]

    @api.model
    def remove_event(self, line_id):
        record_line_id = self.env["product.order.line"].browse(int(line_id))
        if len(record_line_id.product_order_id.product_order_lines_ids.ids) == 1:
            record_line_id.product_order_id.state = "cancel"
        elif len(record_line_id.product_order_id.product_order_lines_ids.ids) > 1:
            record_line_id.unlink()


class productOrderLine(models.Model):
    _name = "product.order.line"
    _description = "product Order Line"

    product_order_id = fields.Many2one("rental.product.order", string="product order")
    product_id = fields.Many2one("product.product", string="product")
    price_based = fields.Selection(
        [("per_day", "Day"), ("per_hour", "Hour"), ("per_session", "Session")],
        default="per_day",
        string="Based On",
    )
    tax_id = fields.Many2many("account.tax", "product_order_tax_rel", string="Tax")
    enter_kms = fields.Float(string="KM")
    enter_hour = fields.Float(string="Hour")
    enter_days = fields.Float(string="Days")
    price = fields.Monetary(string="Price")
    total = fields.Monetary(string="Total")
    sub_total = fields.Monetary(string="Sub Total", compute="_get_subtotal", store=True)
    price_tax = fields.Float(compute="_get_subtotal", string="Taxes", store=True)
    price_total = fields.Monetary(
        compute="`_get_subtotal`", string="Total Price", store=True
    )
    name = fields.Char(string="Description")
    currency_id = fields.Many2one(
        "res.currency", related="product_order_id.currency_id"
    )
    qty_needed = fields.Integer(string="Quantity", default=1)

    @api.onchange("price_based")
    def get_price_value(self):
        self.sub_total = 0.0
        if self.price_based == "per_day":
            self.price = self.product_id.rental_amount
            self.sub_total = (
                self.enter_days * self.qty_needed * self.product_id.rental_amount
            )
        elif self.price_based == "per_hour":
            self.price = self.product_id.rental_amount_per_hour
            self.sub_total = (
                self.enter_hour
                * self.qty_needed
                * self.product_id.rental_amount_per_hour
            )
        else:
            self.price = self.product_id.rental_amount_per_session
            self.sub_total = (
                self.enter_hour
                * self.qty_needed
                * self.product_id.rental_amount_per_session
            )

    @api.onchange("product_id")
    def get_line_value(self):
        if self.product_order_id.from_date and self.product_order_id.to_date:
            if self.price_based == "per_hour":
                self.price = self.product_id.rental_amount_per_hour
            elif self.price_based == "per_day":
                self.price = self.product_id.rental_amount
            else:
                self.price = self.product_id.rental_amount_per_session

        else:
            raise ValidationError(_("Please Select From date Or to date!!!"))

    @api.depends("product_id", "price", "tax_id")
    def _get_subtotal(self):
        for line in self:
            if line.price_based == "per_day":
                qty = line.enter_days * line.qty_needed
            elif line.price_based == "per_session":
                qty = line.qty_needed
            else:
                qty = line.enter_hour * line.qty_needed
            taxes = line.tax_id.compute_all(
                qty, line.product_order_id.currency_id, line.price
            )
            line.update(
                {
                    "price_tax": sum(
                        t.get("amount", 0.0) for t in taxes.get("taxes", [])
                    ),
                    "price_total": taxes["total_included"],
                    "sub_total": taxes["total_excluded"],
                }
            )
            line.get_line_value()


class WizardProductServiceModel(models.TransientModel):
    _name = "wizard.product.service"
    _description = "product Service"
    _inherit = "rental.product.order"

    is_damaged = fields.Boolean(string="Is Damaged")
    service_location_id = fields.Many2one("stock.location", string="Service Location")
    product_location_id = fields.Many2one("stock.location", string="Product Location")

    def confirm_service(self):
        self.state = "confirm"