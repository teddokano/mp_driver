"""
LED controller operation library for MicroPython
Akifumi (Tedd) OKANO / Released under the MIT license

version	0.4 (03-Oct-2022)
version	0.3 (02-Oct-2022)
version	0.2 (01-Oct-2022)
version	0.1 (29-Sep-2022)
"""
from nxp_periph.interface	import	I2C_target, SPI_target


class LED():
	"""
	Make a LED instance
	"""
	
	def __init__( self, controller, channel ):
		"""
		LED initializer
	
		Parameters
		----------
		controller	: machine.I2C instance
		channel		: int
			Output channel

		"""
		self.__dev	= controller
		self.__ch	= channel
	
	@property
	def v( self ):
		pass

	@v.setter
	def v( self, v ):
		"""
		Change PWM setting
		
		Parameters
		----------
		v : int or float
			PWM value
			
		"""
		self.__dev.pwm( self.__ch, v )

	@property
	def i( self ):
		pass

	@i.setter
	def i( self, v ):
		"""
		Change PWM setting
		
		Parameters
		----------
		v : int or float
			Current value
			
		"""
		self.__dev.pwm( self.__ch, v, alt = True )

	@property
	def b( self ):
		pass

	@v.setter
	def b( self, b ):
		"""
		Writing PWM setting value into buffer
		
		Parameters
		----------
		b : int or float
			PWM value stored in buffer
			Need to flush to refrect device behavior.
			
		"""
		self.__dev.buf( self.__ch, b )


class LED_controller_base:
	"""
	An abstraction class to make user interface.
	"""
	def __init__( self, init_val = 0 ):
		self.buffer	= [ 0 ] * self.CHANNELS
		
	def pwm( self, *args, alt = False ):
		"""
		PWM setting

		Takes 1 or 2 arguments.
		
		If 2 arguments are geven, it takes as register-name/address
		and PWM setting value.
		
		If only 1 argument is geven, it takes the agrgument as list.
		The list may need to contain the number of LED controller
		channels (self.CHANNELS) elements.

		Parameters (if 2 arguments given)
		----------
		args[0] : int
			Channel number
		args[1] : int or float
			PWM ratio in range of 0~255 or 0.0~1.0
			
		Parameters (if 1 argument given)
		----------
		args[0] : list
			The list may need to contain the number of LED
			controller channels (self.CHANNELS) elements.
			Values are PWM ratio should be in range of
			0~255 or 0.0~1.0
			
		"""
		reg	= self.__iref_base if alt else self.__pwm_base
		
		if 2 == len( args ):
			r	= reg + args[ 0 ]
			v	= args[ 1 ] if isinstance( args[ 1 ], int ) else int( args[ 1 ] * 255.0 )
			self.write_registers( r, v )
		elif 1 == len( args ):
			l	= [ v if isinstance( v, int ) else int(v * 255.0) for v in args[ 0 ] ]
			self.write_registers( reg, l )
	
	def buf( self, ch, val ):
		"""
		Writing PWM setting value into buffer
		
		Parameters
		----------
		ch : int
			Channel number
		val : int or float
			PWM value stored in buffer
			Need to flush to refrect device behavior.
			
		"""
		self.buffer[ ch ]	= val
		
	def flush( self ):
		"""
		Flash buffer contents into device
		"""
		l	= [ v if isinstance( v, int ) else int(v * 255.0) for v in self.buffer ]
		self.write_registers( self.__pwm_base, l )

class gradation_control():
	HOLDTIME	= [	[ "6",    7 ],
					[ "4",    6 ],
					[ "2",    5 ],
					[ "1",    4 ],
					[ "0.75", 3 ],
					[ "0.50", 2 ],
					[ "0.25", 1 ],
					[ "0",    0 ] 
					]	#	using list instead of dict to keep order of items
	
	def set_gradation( self, group_num, max_iref, time, up = True, down = True, on = 0, off = 0 ):
		reg_i	= "RAMP_RATE_GRP%01d" % group_num

		iref	 = max_iref * 255.0
		time	*= 1000
	
		if time:
			step_duration	= time / iref
			if 32 < step_duration:
				cycle_time		= 8.0
				cycle_time_i	= 1
			else:
				cycle_time		= 0.5
				cycle_time_i	= 0
			
			multi_fctr	= int( step_duration / cycle_time )
			multi_fctr	=  1 if multi_fctr <  1 else multi_fctr
			multi_fctr	= 64 if 64 < multi_fctr else multi_fctr
			
			if multi_fctr == 1:
				iref_inc	= int( iref / (time / cycle_time) )
			else:
				iref_inc	= 1
			
		else:
			cycle_time	= 0
			step_count	= 0
		
		if on < 0.25:	
			on		= 0
			on_i	= 0
		else:
			for item in self.HOLDTIME:
				f	= float( item[ 0 ] )
				if f <= on:
					on		= f
					on_i	= item[ 1 ]
					break

		if off < 0.25:	
			off		= 0
			off_i	= 0
		else:
			for item in self.HOLDTIME:
				f	= float( item[ 0 ] )
				if f <= off:
					off		= f
					off_i	= item[ 1 ]
					break
		
		reg_v	= [	( up << 7 ) | ( down << 6 ) | (iref_inc - 1),	# for RAMP_RATE_GRPn
					( cycle_time_i << 6 ) | (multi_fctr - 1), 		# for STEP_TIME_GRPn
					( on_i << 3) | off_i,							# for HOLD_CNTL_GRPn
					int( iref )										# for IREF_GRPn
					]

		self.write_registers( reg_i, reg_v )
		
		print( "# = {}, max_iref = {}, time = {}, up = {}, down = {}, on = {}, off = {}".format( group_num, max_iref, time, up, down, on, off ) )
		print( "iref          = {}".format( iref ) )
		print( "step_duration = {}".format( step_duration ) )
		print( "cycle_time    = {}".format( cycle_time ) )
		print( "iref_inc      = {}".format( iref_inc ) )
		print( "multi_fctr    = {}".format( multi_fctr ) )
		print( "on            = {}".format( on ) )
		print( "off           = {}".format( off ) )
		print( "iref          = {}".format( iref ) )
		print( "reg_i         = {}".format( reg_i ) )
		print( "reg_v         = {}".format( reg_v ) )
		print( "calc_time     = {}".format( (multi_fctr * cycle_time ) * (iref / iref_inc) ) )

	def gradation_channel_enable( self, list ):
		if type( list ) == int:
			list	= [ list ]
		
		bn	= 0;
		for ch in list:
			bn	|= 0x1 << ch
		
		v	= [ (0xFF & (bn >> (8 * i))) for i in range( self.CHANNELS // 8 ) ]
		self.write_registers( "GRAD_MODE_SEL0", v )
		
		print( v )

	def gradation_group_assign( self, lists ):
		gr_list	= [ 0 ]	* self.CHANNELS
		for gn, l in enumerate( lists ):
			for ch in l:
				gr_list[ ch ]	= gn
		
		print( gr_list )
		
		self.__gradation_groups( gr_list )

	def gradation_start( self, group, continuous = True ):
		if type( group ) == int:
			group	= [ group ]
		
		bit_pattern	= 0
		bit_mask	= 0
		
		for ch in group:
			bit_pattern	|= (0x2 | continuous) << (ch << 1)
			bit_mask	|= 0x3 << (ch << 1)

		print( bit_pattern, bit_mask )

		self.__gradation_start( bit_pattern, bit_mask )

class PCA995xB_base( LED_controller_base, I2C_target ):
	"""
	An abstraction class for PCA995x family
	"""
	DEFAULT_ADDR		= 0xE0 >> 1

	AUTO_INCREMENT		= 0x80
	PWM_INIT			= 0x00
	IREF_INIT			= 0x10

	def __init__( self, i2c, address = DEFAULT_ADDR, pwm = PWM_INIT, iref = IREF_INIT, current_control = False ):
		"""
		PCA995xB_base initializer
	
		Parameters
		----------
		i2c		: machine.I2C instance
		address	: int
			I2C target (device) address
		pwm		: int, option
			Initial PWM value
		iref	: int, option
			Initial IREF (current setting) value
		current_control : bool, option
			Brightness control switch PWM or current.
			Default:PWM (False)

		"""
		I2C_target.__init__( self, i2c, address, auto_increment_flag = self.AUTO_INCREMENT )
		LED_controller_base.__init__( self, init_val = iref if current_control else pwm )
		
		self.__pwm_base		= self.REG_NAME.index( "IREF0" if current_control else "PWM0"  )
		self.__iref_base	= self.REG_NAME.index( "PWM0"  if current_control else "IREF0" )
		
		init	=	{
						"LEDOUT0": [ 0xAA ] * (self.CHANNELS // 4),
						"PWMALL" : pwm,
						"IREFALL": iref
					}
					
		for r, v in init.items():	#	don't care: register access order
			self.write_registers( r, v )

	def dump( self ):
		data	= super().dump()
		start	= self.REG_NAME.index( "PWMALL" )

		for i in range( start, len( self.REG_NAME ) ):
			data[ i ]	= self.read_registers( i, 1 )
			
		return data

class PCA9955B( PCA995xB_base, gradation_control ):
	CHANNELS		= 16
	GRAD_GRPS		=  4
	REG_NAME		=	(
							"MODE1", "MODE2",
							"LEDOUT0", "LEDOUT1", "LEDOUT2", "LEDOUT3",
							"GRPPWM", "GRPFREQ",
							"PWM0",  "PWM1", "PWM2",  "PWM3",  "PWM4",  "PWM5",  "PWM6",  "PWM7",
							"PWM8",  "PWM9", "PWM10", "PWM11", "PWM12", "PWM13", "PWM14", "PWM15",
							"IREF0", "IREF1", "IREF2",  "IREF3",  "IREF4",  "IREF5",  "IREF6",  "IREF7",
							"IREF8", "IREF9", "IREF10", "IREF11", "IREF12", "IREF13", "IREF14", "IREF15",
							"RAMP_RATE_GRP0", "STEP_TIME_GRP0", "HOLD_CNTL_GRP0", "IREF_GRP0",
							"RAMP_RATE_GRP1", "STEP_TIME_GRP1", "HOLD_CNTL_GRP1", "IREF_GRP1",
							"RAMP_RATE_GRP2", "STEP_TIME_GRP2", "HOLD_CNTL_GRP2", "IREF_GRP2",
							"RAMP_RATE_GRP3", "STEP_TIME_GRP3", "HOLD_CNTL_GRP3", "IREF_GRP3",
							"GRAD_MODE_SEL0", "GRAD_MODE_SEL1",
							"GRAD_GRP_SEL0", "GRAD_GRP_SEL1", "GRAD_GRP_SEL2", "GRAD_GRP_SEL3",
							"GRAD_CNTL",
							"OFFSET",
							"SUBADR1", "SUBADR2", "SUBADR3", "ALLCALLADR",
							"PWMALL", "IREFALL",
							"EFLAG0", "EFLAG1", "EFLAG2", "EFLAG3"
						)
						
	def __gradation_groups( self, list ):
		bn	= 0
		for i, ch in enumerate( list ):
			bn	|= ch << (i << 1)
		
		v	= [ (0xFF & (bn >> (8 * i))) for i in range( self.GRAD_GRPS ) ]
		self.write_registers( "GRAD_GRP_SEL0", v )
		
		print( v )
	
	def __gradation_start( self, pattern, mask ):
		self.bit_operation( "GRAD_CNTL", mask, pattern )
	
class PCA9956B( PCA995xB_base ):
	CHANNELS		= 24
	REG_NAME		=	(
							"MODE1", "MODE2",
							"LEDOUT0", "LEDOUT1", "LEDOUT2", "LEDOUT3", "LEDOUT4", "LEDOUT5",
							"GRPPWM", "GRPFREQ",
							"PWM0",  "PWM1",  "PWM2",  "PWM3",  "PWM4",  "PWM5",
							"PWM6",  "PWM7",  "PWM8",  "PWM9",  "PWM10", "PWM11",
							"PWM12", "PWM13", "PWM14", "PWM15", "PWM16", "PWM17",
							"PWM18", "PWM19", "PWM20", "PWM21", "PWM22", "PWM23",
							"IREF0",  "IREF1",  "IREF2",  "IREF3",  "IREF4",  "IREF5",
							"IREF6",  "IREF7",  "IREF8",  "IREF9",  "IREF10", "IREF11",
							"IREF12", "IREF13", "IREF14", "IREF15", "IREF16", "IREF17",
							"IREF18", "IREF19", "IREF20", "IREF21", "IREF22", "IREF23",
							"OFFSET",
							"SUBADR1", "SUBADR2", "SUBADR3", "ALLCALLADR",
							"PWMALL", "IREFALL",
							"EFLAG0", "EFLAG1", "EFLAG2", "EFLAG3", "EFLAG4", "EFLAG5"
						)

class PCA96xx_base( LED_controller_base, I2C_target ):
	"""
	An abstraction class for PCA995x family
	"""
	DEFAULT_ADDR		= 0xC4 >> 1

	AUTO_INCREMENT		= 0x80
	PWM_INIT			= 0x00

	def __init__( self, i2c, address = DEFAULT_ADDR, pwm = PWM_INIT ):
		"""
		PCA995xB_base initializer
	
		Parameters
		----------
		i2c		: machine.I2C instance
		address	: int
			I2C target (device) address
		pwm		: int, option
			Initial PWM value

		"""
		I2C_target.__init__( self, i2c, address, auto_increment_flag = self.AUTO_INCREMENT )
		LED_controller_base.__init__( self, init_val = pwm )
		
		self.__pwm_base	= self.REG_NAME.index( "PWM0" )
		


class PCA9632( PCA96xx_base ):
	CHANNELS		= 4
	REG_NAME		=	(
							"MODE1", "MODE2",
							"PWM0",  "PWM1",  "PWM2",  "PWM3",
							"GRPPWM", "GRPFREQ",
							"LEDOUT",
							"SUBADR1", "SUBADR2", "SUBADR3", "ALLCALLADR",
						)
	DEFAULT_ADDR	= 0xC4 >> 1
	PWM_INIT		= 0x00

	def __init__( self, i2c, address = DEFAULT_ADDR, pwm = PWM_INIT ):
		super().__init__( i2c, address = address, pwm = pwm )
		init	=	{
						"MODE1": 0x81,
						"MODE2": 0x01,
						"LEDOUT": 0xAA,
						"PWM0": [ pwm ] * self.CHANNELS
					}
					
		for r, v in init.items():	#	don't care: register access order
			self.write_registers( r, v )


class PCA9957_base( LED_controller_base, gradation_control, SPI_target ):
	"""
	An abstraction class for PCA9957 family
	"""
	PWM_INIT			= 0x00
	IREF_INIT			= 0x10

	def __init__( self, spi, cs = None, pwm = PWM_INIT, iref = IREF_INIT, current_control = False, setup_EVB = False ):
		"""
		PCA995xB_base initializer
	
		Parameters
		----------
		spi		: machine.SPI instance
		cs		: machine.Pin instance
		pwm		: int, option
			Initial PWM value
		iref	: int, option
			Initial IREF (current setting) value
		current_control : bool, option
			Brightness control switch PWM or current.
			Default:PWM (False)

		"""
		SPI_target.__init__( self, spi, cs )
		
		if setup_EVB:
			self.__setup_EVB()
			
		LED_controller_base.__init__( self, init_val = iref if current_control else pwm )

		self.__pwm_base		= self.REG_NAME.index( "IREF0" if current_control else "PWM0" )
		self.__iref_base	= self.REG_NAME.index( "PWM0"  if current_control else "IREF0" )

		for r, v in { 0xFF: 0xFF, 0xFE: 0xFE, 0xFD: 0xFD }.items():
			self.write_registers( r, v )
		
		init	=	{
						"MODE2"		: 0x18,		#	to forth the channel working when wrror happened
						"LEDOUT0"	: [ 0xAA ] * (self.CHANNELS // 4),
						"PWMALL"	: pwm,
						"IREFALL"	: iref
					}
					
		for r, v in init.items():	#	don't care: register access order
			self.write_registers( r, v )
	
	def write_registers( self, reg, data ):
		"""
		writing register
	
		Parameters
		----------
		reg : string or int
			Register name or register address/pointer.
		data : list or int
			Data for sending.
			List for multibyte sending. List is converted to
			bytearray before sending.
			If the data is integer, single byte will be sent.
			
		"""
		#print( "write_registers: {}, {}".format( reg, data ) )
		
		data		= [ data ] if type(data) == int else data

		reg			= self.REG_NAME.index( reg ) if type( reg ) != int else reg
		reg_list	= [ i << 1 for i in range( reg, reg + len( data ) ) ]

		for r, v in zip( reg_list, data ):
			self.send( [ r, v ] )
			
	def read_registers( self, reg, length ):
		"""
		reading register
	
		Parameters
		----------
		reg : string or int
			Register name or register address/pointer.
		length : int
			Number of bytes for receiveing.
		repeated_start : bool, option
			If True, a Repeated-START-condition generated between
			write and read transactions.
			If False, a STOP-condition and START-condition are
			generated between write and read transactions.
		"""
		data		= [ 0xFF ] * length
		reg			= self.REG_NAME.index( reg ) if type( reg ) != int else reg
		reg_list	= [ (i << 1) | 0x01 for i in range( reg, reg + len( data ) ) ]

		pairs	= []
		for r, v in zip( reg_list, data ):
			self.send( [ r, v ] )
			pairs	+= [self.receive( [ 0xFF, 0xFF ] )]
		
		rtn	= []
		for p in pairs:
			rtn	+= [ p[ 1 ] ]

		return rtn[ 0 ] if 1 == length else rtn

	def __setup_EVB( self ):
		"""
		setting up RESET and OE pins on PCA9957HN_ARD evaluation board
		
		"""
		from machine import Pin
		print( "PCA9957HN_ARD setting done." )
		rst	= Pin( "D8", Pin.OUT )
		oe	= Pin( "D9", Pin.OUT )
		rst.value( 1 )
		oe.value( 0 )



class PCA9957( PCA9957_base ):
	CHANNELS		= 24
	GRAD_GRPS		=  4

	REG_NAME		=	(
							"MODE1", "MODE2",
							"EFLAG0",  "EFLAG1",  "EFLAG2",  "EFLAG3",  "EFLAG4",  "EFLAG5",
							"LEDOUT0", "LEDOUT1", "LEDOUT2", "LEDOUT3", "LEDOUT4", "LEDOUT5",
							"GRPPWM", "GRPFREQ",
							"PWM0",  "PWM1",  "PWM2",  "PWM3",  "PWM4",  "PWM5",
							"PWM6",  "PWM7",  "PWM8",  "PWM9",  "PWM10", "PWM11",
							"PWM12", "PWM13", "PWM14", "PWM15", "PWM16", "PWM17",
							"PWM18", "PWM19", "PWM20", "PWM21", "PWM22", "PWM23",
							"IREF0",  "IREF1",  "IREF2",  "IREF3",  "IREF4",  "IREF5",
							"IREF6",  "IREF7",  "IREF8",  "IREF9",  "IREF10", "IREF11",
							"IREF12", "IREF13", "IREF14", "IREF15", "IREF16", "IREF17",
							"IREF18", "IREF19", "IREF20", "IREF21", "IREF22", "IREF23",
							"RAMP_RATE_GRP0", "STEP_TIME_GRP0", "HOLD_CNTL_GRP0", "IREF_GRP0",
							"RAMP_RATE_GRP1", "STEP_TIME_GRP1", "HOLD_CNTL_GRP1", "IREF_GRP1",
							"RAMP_RATE_GRP2", "STEP_TIME_GRP2", "HOLD_CNTL_GRP2", "IREF_GRP2",
							"RAMP_RATE_GRP3", "STEP_TIME_GRP3", "HOLD_CNTL_GRP3", "IREF_GRP3",
							"RAMP_RATE_GRP4", "STEP_TIME_GRP4", "HOLD_CNTL_GRP4", "IREF_GRP4",
							"RAMP_RATE_GRP5", "STEP_TIME_GRP5", "HOLD_CNTL_GRP5", "IREF_GRP5",
							"GRAD_MODE_SEL0", "GRAD_MODE_SEL1", "GRAD_MODE_SEL2",
							"GRAD_GRP_SEL0",  "GRAD_GRP_SEL1",  "GRAD_GRP_SEL2",
							"GRAD_GRP_SEL3",  "GRAD_GRP_SEL4",  "GRAD_GRP_SEL5",
							"GRAD_GRP_SEL6",  "GRAD_GRP_SEL7",  "GRAD_GRP_SEL8",
							"GRAD_GRP_SEL9",  "GRAD_GRP_SEL10", "GRAD_GRP_SEL11",
							"GRAD_CNTL0", "GRAD_CNTL1",
							"OFFSET",
							"PWMALL", "IREFALL"
						)

