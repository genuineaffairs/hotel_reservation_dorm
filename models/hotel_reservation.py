from openerp import models, fields, api, exceptions
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import datetime
import time

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
				# Create a reservation on a bed if the room is a dorm
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
				# Create a reservation on the room
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
				'service_lines': reservation['folio_id'],
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
					#  Logic for creation of multiple folio.lines for dorm-rooms
					nr_of_lines_to_create = 1
					if r.dormitory:
						nr_of_lines = reservation.adults + reservation.children
					# --------------------
					for i in range(nr_of_lines_to_create):
						folio_lines.append((0, 0, {
							'checkin_date': checkin_date,
							'checkout_date': checkout_date,
							'product_id': r.product_id and r.product_id.id,
							'name': reservation['reservation_no'],
							'product_uom': prod_uom,
							'price_unit': price_unit,
							'product_uom_qty': ((date_a - date_b).days) + 1,
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
		
class RoomReservationSummary(models.Model):
	_inherit = 'room.reservation.summary'
	
	# Override get_room_summary to include dorm-functionality
	@api.onchange('date_from', 'date_to')
	def get_room_summary(self):
		'''
		@param self: object pointer
		 '''
		res = {}
		all_detail = []
		room_obj = self.env['hotel.room']
		reservation_line_obj = self.env['hotel.room.reservation.line']
		folio_room_line_obj = self.env['folio.room.line']
		date_range_list = []
		main_header = []
		summary_header_list = ['Rooms']
		if self.date_from and self.date_to:
			if self.date_from > self.date_to:
				raise except_orm(_('User Error!'),
								 _('Please Check Time period Date \
								 From can\'t be greater than Date To !'))					 
			# Add a time at the end of the day to make reservation-summary functionality work
			# properly with timezone and show the correct dates as reserved/free
			temp_from = fields.Datetime.from_string(self.date_from)
			d_frm_obj = temp_from.replace(temp_from.year,temp_from.month,temp_from.day,23,00,00)
			temp_to = fields.Datetime.from_string(self.date_to)
			d_to_obj = temp_to.replace(temp_to.year,temp_to.month,temp_to.day,23,00,00)

			temp_date = d_frm_obj
			while(temp_date <= d_to_obj):
				val = ''
				val = (str(temp_date.strftime("%a")) + ' ' +
					   str(temp_date.strftime("%b")) + ' ' +
					   str(temp_date.strftime("%d")))
				summary_header_list.append(val)
				date_range_list.append(temp_date.strftime
									   (DEFAULT_SERVER_DATETIME_FORMAT))
				temp_date = temp_date + datetime.timedelta(days=1)
			all_detail.append(summary_header_list)
			room_ids = room_obj.search([])
			all_room_detail = []
			for room in room_ids:
				room_detail = {}
				room_list_stats = []
				room_detail.update({'name': room.name or ''})
				# Include a check for dorm_reservation_line_ids
				if not room.room_reservation_line_ids and \
				   not room.room_line_ids and not room.dorm_reservation_line_ids:
					for chk_date in date_range_list:
						room_list_stats.append({'state': 'Free',
												'date': chk_date})
				else:
					for chk_date in date_range_list:
						reserline_ids = room.room_reservation_line_ids.ids
						reservline_ids = (reservation_line_obj.search
										  ([('id', 'in', reserline_ids),
											('check_in', '<=', chk_date),
											('check_out', '>=', chk_date),
											('status', '!=', 'cancel')
											]))
						fol_room_line_ids = room.room_line_ids.ids
						chk_state = ['draft', 'cancel']
						folio_resrv_ids = (folio_room_line_obj.search
										   ([('id', 'in', fol_room_line_ids),
											 ('check_in', '<=', chk_date),
											 ('check_out', '>=', chk_date),
											 ('status', 'not in', chk_state)
											 ]))
						# Make a check for bed_reservation_line_ids in case of dorm-room
						# If number of bed reservations is equal to the room capacity -> the room is occupied
						dorm_occupied = 0
						if room.dormitory:
							bed_res_ids = room.dorm_reservation_line_ids.ids
							bed_reservations = (reservation_line_obj.search
										  ([('id', 'in', bed_res_ids),
											('check_in', '<=', chk_date),
											('check_out', '>=', chk_date),
											('status', '!=', 'cancel')
											]))
						# Include a check for the dorm_occupied-flag
						if reservline_ids or folio_resrv_ids or dorm_occupied:
							room_list_stats.append({'state': 'Reserved',
													'date': chk_date,
													'room_id': room.id,
													'is_draft': 'No',
													'data_model': '',
													'data_id': 0})
						else:
							room_list_stats.append({'state': 'Free',
													'date': chk_date,
													'room_id': room.id})

				room_detail.update({'value': room_list_stats})
				all_room_detail.append(room_detail)
			main_header.append({'header': summary_header_list})
			self.summary_header = str(main_header)
			self.room_summary = str(all_room_detail)
		return res