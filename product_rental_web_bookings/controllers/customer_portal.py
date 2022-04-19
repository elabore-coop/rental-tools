# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        rental_order_detail = request.env["rental.product.order"].sudo()
        rental_order_count = rental_order_detail.search_count(
            [("customer_name", "=", request.env.user.partner_id.id)]
        )
        values.update(
            {
                "rental_order_count": rental_order_count,
            }
        )
        return values

    @http.route("/order", type="http", auth="public", website=True)
    def order(self, page=1, date_begin=None, date_end=None, sortby=None):
        values = self._prepare_portal_layout_values()
        order_id = (
            request.env["rental.product.order"]
            .sudo()
            .search([("customer_name", "=", request.env.user.partner_id.id)])
        )
        searchbar_sortings = {
            "date": {"label": ("Start Date"), "order": "from_date desc"},
            "date1": {"label": ("End Date"), "order": "to_date desc"},
            "stage": {"label": ("Stage"), "order": "state"},
        }
        # default sortby order
        if not sortby:
            sortby = "date"
        sort_order = searchbar_sortings[sortby]["order"]
        values.update(
            {
                "order_id": order_id,
                "page_name": "rental_order",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("product_rental_bookings.rental_order", values)
