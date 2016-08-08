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
			
	@api.model
	def create(self, vals):	
		if not vals:
			vals = {}
		if self._context is None:
			self._context = {}
		vals['reservation_no'] = self.env['ir.sequence'].get('hotel.reservation')
		# EXTRA
		# Set checkin/out times
		temp_checkin = fields.Datetime.from_string(vals['checkin'])
		temp_checkout = fields.Datetime.from_string(vals['checkout'])
		temp_checkin = temp_checkin.replace(temp_checkin.year,temp_checkin.month,temp_checkin.day,17,00,00)
		temp_checkout = temp_checkout.replace(temp_checkout.year,temp_checkout.month,temp_checkout.day,15,00,00)
		vals['checkin'] = temp_checkin
		vals['checkout'] = temp_checkout
		# END OF EXTRA
		return super(HotelReservation, self).create(vals)