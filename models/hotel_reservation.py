from openerp import models, fields, api

class HotelReservation(models.Model):
	_inherit = 'hotel.reservation'
	
	def test_func(res):
		print "TEST RESULT"
		print ""
		print res

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
			print "PRINT RES:"
			print ""
			print res
			roomcount = res and res[0] or 0.0
			if roomcount:
				raise except_orm(_('Warning'), _('You tried to confirm \
				reservation with room those already reserved in this \
				reservation period'))
			else:
				self.write({'state': 'confirm'})
				for line_id in reservation.reservation_line:
					line_id = line_id.reserve
					for room_id in line_id:
						vals = {
							'room_id': room_id.id,
							'check_in': reservation.checkin,
							'check_out': reservation.checkout,
							#'state': 'assigned',
							'reservation_id': reservation.id,
							}
						room_id.write({'isroom': True, 'status': 'available'})
						reservation_line_obj.create(vals)
		return True
		