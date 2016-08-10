from openerp import models, fields, api, exceptions

class HotelReservation(models.Model):
	_inherit = 'hotel.reservation'

	@api.multi
	def confirmed_reservation(self):
		"""
		This method create a new recordset for hotel room reservation line
		------------------------------------------------------------------
		@param self: The object pointer
		@return: new record set for hotel room reservation line.
		"""
		reservation_line_obj = self.env['hotel.room.reservation.line']
		for reservation in self:
			roomcount = 0
			room_id = reservation.reservation_line.reserve
			beds_to_reserv = []
			# Check if the reservation is for a room marked as dormitory
			if room_id.dormitory:
				persons = self.adults + self.children
				for bed in room_id.bed_ids:
					# Check availability for each bed and append it to beds_to_reserv if available
					ret = bed.check_availability(self.checkin, self.checkout)
					if ret[0]:
						beds_to_reserv.append(bed.id)
						if (persons == len(beds_to_reserv)):
							break
				if (persons != len(beds_to_reserv)):
					roomcount = 1
			else:
				self._cr.execute("select count(*) from hotel_reservation as hr "
					"inner join hotel_reservation_line as hrl on \
					hrl.line_id = hr.id "
					"inner join hotel_reservation_line_room_rel as \
					hrlrr on hrlrr.room_id = hrl.id "
					"where (checkin,checkout) overlaps \
					( timestamp %s, timestamp %s ) "
					"and hr.id <> cast(%s as integer) "
					"and hr.state = 'confirm' "
					"and hrlrr.hotel_reservation_line_id in ("
					"select hrlrr.hotel_reservation_line_id \
					from hotel_reservation as hr "
					"inner join hotel_reservation_line as \
					hrl on hrl.line_id = hr.id "
					"inner join hotel_reservation_line_room_rel \
					as hrlrr on hrlrr.room_id = hrl.id "
					"where hr.id = cast(%s as integer) )",
					(reservation.checkin, reservation.checkout,
					str(reservation.id), str(reservation.id)))
				res = self._cr.fetchone()
				roomcount = res and res[0] or 0.0
			if roomcount:
				raise exceptions.Warning('You tried to confirm \
				a reservation for a room that is already reserved in this \
				reservation period')
			else:
				self.write({'state': 'confirm'})
				# EXTRA. Create a reservation on a bed if the room is a dorm
				if room_id.dormitory:
					for bed_id in beds_to_reserv:
						vals = {
							'dorm_id': room_id.id,
							'bed_id': bed_id,
							'check_in': reservation.checkin,
							'check_out': reservation.checkout,
							'state': 'assigned',
							'reservation_id': reservation.id,								
							}
						reservation_line_obj.create(vals)
				else:
				# END OF EXTRA
					vals = {
						'room_id': room_id.id,
						'check_in': reservation.checkin,
						'check_out': reservation.checkout,
						'state': 'assigned',
						'reservation_id': reservation.id,
						}
					room_id.write({'isroom': False, 'status': 'occupied'})
					reservation_line_obj.create(vals)
		return True
			
@api.multi
    def _create_folio(self):
        """
        This method is for create new hotel folio.
        -----------------------------------------
        @param self: The object pointer
        @return: new record set for hotel folio.
        """
        hotel_folio_obj = self.env['hotel.folio']
        room_obj = self.env['hotel.room']
        for reservation in self:
            folio_lines = []
            checkin_date = reservation['checkin']
            checkout_date = reservation['checkout']
            if not self.checkin < self.checkout:
                raise except_orm(_('Error'),
                                 _('Checkout date should be greater \
                                 than the Checkin date.'))
            duration_vals = (self.onchange_check_dates
                             (checkin_date=checkin_date,
                              checkout_date=checkout_date, duration=False))
            duration = duration_vals.get('duration') or 0.0
            folio_vals = {
                'date_order': reservation.date_order,
                'warehouse_id': reservation.warehouse_id.id,
                'partner_id': reservation.partner_id.id,
                'pricelist_id': reservation.pricelist_id.id,
                'partner_invoice_id': reservation.partner_invoice_id.id,
                'partner_shipping_id': reservation.partner_shipping_id.id,
                'checkin_date': reservation.checkin,
                'checkout_date': reservation.checkout,
                'duration': duration,
                'reservation_id': reservation.id,
                'service_lines': reservation['folio_id']
            }
            date_a = (datetime.datetime
                      (*time.strptime(reservation['checkout'],
                                      DEFAULT_SERVER_DATETIME_FORMAT)[:5]))
            date_b = (datetime.datetime
                      (*time.strptime(reservation['checkin'],
                                      DEFAULT_SERVER_DATETIME_FORMAT)[:5]))
            for line in reservation.reservation_line:
                for r in line.reserve:
                    prod = r.product_id.id
                    partner = reservation.partner_id.id
                    price_list = reservation.pricelist_id.id
                    folio_line_obj = self.env['hotel.folio.line']
                    prod_val = folio_line_obj.product_id_change(
                        pricelist=price_list, product=prod,
                        qty=0, uom=False, qty_uos=0, uos=False,
                        name='', partner_id=partner, lang=False,
                        update_tax=True, date_order=False
                    )
                    prod_uom = prod_val['value'].get('product_uom', False)
                    price_unit = prod_val['value'].get('price_unit', False)
                    folio_lines.append((0, 0, {
                        'checkin_date': checkin_date,
                        'checkout_date': checkout_date,
                        'product_id': r.product_id and r.product_id.id,
                        'name': reservation['reservation_no'],
                        'product_uom': prod_uom,
                        'price_unit': price_unit,
                        'product_uom_qty': ((date_a - date_b).days) + 1,
						'product_uos_qty': 2,
                        'is_reserved': True}))
                    res_obj = room_obj.browse([r.id])
                    res_obj.write({'status': 'occupied', 'isroom': False})
            folio_vals.update({'room_lines': folio_lines})
            folio = hotel_folio_obj.create(folio_vals)
            self._cr.execute('insert into hotel_folio_reservation_rel'
                            '(order_id, invoice_id) values (%s,%s)',
                             (reservation.id, folio.id)
                             )
            reservation.write({'state': 'done'})
        return True			

	@api.model
	def create(self, vals):	
		if not vals:
			vals = {}
		if self._context is None:
			self._context = {}
		vals['reservation_no'] = self.env['ir.sequence'].get('hotel.reservation')
		# EXTRA
		# Set checkin/out times greater than 00:00:00 UTC to display the correct dates with timezone
		# Checkin time needs to be greater than checkout time so one night is less then 24hours to create folio correctly
		temp_checkin = fields.Datetime.from_string(vals['checkin'])
		temp_checkout = fields.Datetime.from_string(vals['checkout'])
		temp_checkin = temp_checkin.replace(temp_checkin.year,temp_checkin.month,temp_checkin.day,17,00,00)
		temp_checkout = temp_checkout.replace(temp_checkout.year,temp_checkout.month,temp_checkout.day,15,00,00)
		vals['checkin'] = temp_checkin
		vals['checkout'] = temp_checkout
		# END OF EXTRA
		return super(HotelReservation, self).create(vals)