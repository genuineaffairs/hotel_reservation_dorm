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
			next_free_bed = 0
			# Check if the reservation is for a room marked as dormitory
			if room_id.dormitory:
				for bed in room_id.bed_ids:
					# Check availability for each bed and set it to next_free_bed if available
					ret = bed.check_availability(self.checkin, self.checkout)
					if ret[0]:
						next_free_bed = bed
						break
				if not next_free_bed:
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
					vals = {
						'dorm_id': room_id.id,
						'bed_id': next_free_bed.id,
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
		# OVERRIDE
		temp_checkin = fields.Datetime.from_string(vals['checkin'] + " 08:00:00")
		temp_checkout = fields.Datetime.from_string(vals['checkout'] + " 06:00:00")
		print temp_checkin
		print temp_checkout
		# OVERRIDE	
		return super(HotelReservation, self).create(vals)