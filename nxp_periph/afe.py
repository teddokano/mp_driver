from	machine		import	SPI, Pin, Timer
from	utime		import	sleep, sleep_ms, sleep_us
from	struct		import	unpack
from	micropython	import	schedule
from nxp_periph.interface	import	SPI_target
from nxp_periph.MikanUtil	import	MikanUtil

WAIT	= 0.001
#WAIT	= 0
CWAIT	= 0

class AFE_base:
	"""
	An abstraction class to make user interface.
	"""
	pass

class NAFE13388( AFE_base, SPI_target ):
	"""
	NAFE13388: Analog Front-End
	
	A device class for a 8 channel AFE
	This class enables to get its measured voltage
	
	"""
	ch_cnfg_reg	= [ 0x0020, 0x0021, 0x0022, 0x0023 ]

	def __init__( self, spi, cs = None ):
		"""
		NAFE13388 initializer
	
		Parameters
		----------
		spi		: machine.SPI instance
		cs		: machine.Pin instance

		"""
		self.tim_flag	= False
		self.cb_count	= 0

		SPI_target.__init__( self, spi, cs )

		"""
		###	For original EVB
		self.reset_pin	= Pin( "D6", Pin.OUT )
		self.syn_pin	= Pin( "D5", Pin.OUT )
		self.drdy_pin	= Pin( "D3", Pin.IN )
		self.int_pin	= Pin( "D2", Pin.IN )
		"""

		###	For UIM
		self.reset_pin	= Pin( "D7", Pin.OUT )
		self.syn_pin	= Pin( "D6", Pin.OUT )
		self.drdy_pin	= Pin( "D4", Pin.IN )
		self.int_pin	= Pin( "D3", Pin.IN )

		
		self.reset_pin.value( 1 )
		self.syn_pin.value( 1 )
		
		self.reset()
		self.boot()
		
		self.pga_gain			= [ 0.2, 0.4, 0.8, 1, 2, 4, 8, 16 ]
		self.coeff_microvolt	= [ 0 ] * 16
		
		self.logical_channel	= [
									# self.logical_ch_config( 0, [ 0x1150, 0x00AC, 0x1400, 0x0000 ] ),
									# self.logical_ch_config( 1, [ 0x3350, 0x00A4, 0x1400, 0x3060 ] ),
									self.logical_ch_config( 0, [ 0x22F0, 0x70AC, 0x5800, 0x0000 ] ),
									self.logical_ch_config( 1, [ 0x33F0, 0x70B1, 0x5800, 0x3860 ] ),
									self.logical_ch_config( 0, [ 0x1070, 0x0084, 0x2900, 0x0000 ] ),
									self.logical_ch_config( 1, [ 0x2070, 0x0084, 0x2900, 0x0000 ] ),
									]

		print( f"================ self.num_logcal_ch = {self.num_logcal_ch}" )

		self.ch		= [ 0 ] * self.num_logcal_ch
		self.done	= False
		
	def periodic_measurement_start( self ):
		"""
		AFE periodic operation starter
		"""
		tim0 = Timer( MikanUtil.get_timer_id( 0 ) )
		tim0.init( period= 100, callback = self.tim_cb )

	def sch_cb( self, _ ):
		"""
		AFE periodic operation callback via tim_cb()
		"""
		ch_start	= (self.cb_count + 1) % 2
		ch_read		= self.cb_count % 2

		# read data
		self.ch[ ch_read ]	= self.read_r24( 0x2040 + ch_read )	* self.coeff_microvolt[ ch_read ]

		# start ADC operation
		self.write_r16( 0x0000 + ch_start )
		self.write_r16( 0x2000 )
		
		self.cb_count	+= 1
		
		if self.cb_count % 2:
			self.done	= True
	
	def tim_cb( self, tim_obj ):
		"""
		timer callback
		"""
		schedule( self.sch_cb, 0 )

	def	write_r16( self, reg, val = None ):
		"""
		writing 16bit register
	
		Parameters
		----------
		reg : int
			Register address/pointer.
		val : int
			16bit data
			
		"""
		reg		<<= 1
	
		regH	= reg >> 8 & 0xFF
		regL	= reg & 0xFF

		if val is None:
			self.send( [ regH, regL ] )
		else:
			valH	= val >> 8 & 0xFF
			valL	= val & 0xFF
			self.send( [ regH, regL, valH, valL ] )

	def	read_r16( self, reg, signed = False ):
		"""
		reading 16bit register
	
		Parameters
		----------
		reg : int
			Register address/pointer.
		signed : bool
			Switch to select the data in signed or unsigned (default: signed)
			
		Returns
		-------
		int : register value

		"""
		reg		<<= 1
		reg		|= 0x4000
		regH	= reg >> 8 & 0xFF
		regL	= reg & 0xFF

		data	= bytearray( [ regH, regL, 0xFF, 0xFF ] )
		self.__if.write_readinto( data, data )
		
		return unpack( ">h" if signed else ">H", data[2:] )[ 0 ]

	def	read_r24( self, reg ):
		"""
		reading 24bit register
	
		Parameters
		----------
		reg : int
			Register address/pointer.
			
		Returns
		-------
		int : register value

		"""
		reg		<<= 1
		reg		|= 0x4000
		regH	= reg >> 8 & 0xFF
		regL	= reg & 0xFF

		data	= bytearray( [ regH, regL, 0xFF, 0xFF, 0xFF ] )
		self.__if.write_readinto( data, data )

		data	+= b'\x00'		
		data	= unpack( ">l", data[2:] )[ 0 ] >> 8

		return data

	def boot( self ):
		"""
		Boot-up procedure
		"""
		reg_init	= [
						{	0x0010: None, 
							0x002A: 0x0000,
							0x002B: 0x0000,
							0x002C: 0x0000,
							0x002F: 0x0000,
							0x0029: 0x0000,
							},
						{	0x0030: 0x0010, 
							},
					]
					
		for step in reg_init:
			for k, v in step.items():
				self.write_r16( k, v )
			sleep( WAIT )

	def reset( self ):
		"""
		Reset procedure
		"""
		self.write_r16( 0x0014 )
		sleep( WAIT )

	def dump( self, list ):
		"""
		Register dump

		Parameters
		----------
		list : list
			List of register address/pointer.
		"""
		for r in list:
			if r:
				print( "0x{:04X} = {:04X}".format( r, self.read_r16( r ) ) )
			else:
				print( "" )

	def logical_ch_config( self, logical_channel, list ):
		"""
		Logical channel configuration

		Parameters
		----------
		list : list
			List of register values for register 0x20, 0x21, 0x22 and 0x23
			
		"""
		for r in list:
			if r:
				print( "0x{:04X} = {:04X}".format( r, self.read_r16( r ) ) )
			else:
				print( "" )
		self.write_r16( 0x0000 + logical_channel )

		for r, v in zip( self.ch_cnfg_reg, list ):
			self.write_r16( r, v )
		self.dump( [ 0x20, 0x21, 0x22, 0x23 ] )
		
		mask	= 1
		bits	= self.read_r16( 0x24 ) | mask << logical_channel
		self.write_r16( 0x24, bits )
		
		print( f"bits = {bits}" )
		print( f"self.read_r16( 0x24 ) = {self.read_r16( 0x24 )}" )
		
		cc0	= list[ 0 ]
		
		if cc0 & 0x0010:
			self.coeff_microvolt[ logical_channel ]	= ((10.0 / (1 << 24)) / self.pga_gain[ (cc0 >> 5) & 0x7 ]) * 1e6
		else:
			self.coeff_microvolt[ logical_channel ]	= (4.0 / (1 << 24)) * 1e6;

		
		self.num_logcal_ch	= 0
		for i in range( 16 ):
			if bits & (mask << i):
				self.num_logcal_ch	+= 1
		
		print( f"self.num_logcal_ch = {self.num_logcal_ch}" )
		
	def measure( self, ch = None ):
		"""
		Measure input voltage

		Parameters
		----------
		ch : int
			Logical input channel number or None
			
		Returns
		-------
		float in voltage (microvolt) if "ch" was given
		list of raw measured values if "ch" was not given

		"""
		if ch is not None:
			self.write_r16( 0x0000 + ch )
			self.write_r16( 0x2000 )
#			sleep_ms( 100 )
			sleep_ms( 50 )
			return self.read_r24( 0x2040 + ch ) * self.coeff_microvolt[ ch ]
		
		values	= []

		command	= 0x2004

		for i in range( self.num_logcal_ch ):
			self.write_r16( command )
			"""
			print( f"after command" )
			for i in range( 100 ):
				print( f"0x31 = {self.read_r16( 0x31 ):04X}" )
				sleep_us( 10 )
			"""
			sleep_ms( 10 )
			values	+= [ self.read_r24( 0x2040 + i ) ]
		
		print( values )

		return values
		
	def read( self, ch = None ):
		"""
		Read input value

		Parameters
		----------
		ch : int
			Logical input channel number or None
			This part need to be implemented
			
		Returns
		-------
		list of raw measured values if "ch" was not given

		"""
		values	= []

		for i in range( self.num_logcal_ch ):
			values	+= [ self.read_r24( 0x2040 + i ) ]
		
		print( values )

		return values
	
	def die_temp( self ):
		"""
		Die temperature
		
		Returns
		-------
		float : Die temperature in celcius

		"""
		return self.read_r16( 0x34, signed = True ) / 64
		
def main():
	spi	= SPI( 0, 1000_000, cs = 0, phase = 1 )

	afe	= NAFE13388( spi, None )
	afe.dump( [ 0x7C, 0x7D, 0x7E, 0xAE, 0xAF, 0x34, 0x37, None, 0x30, 0x31 ] )
	
	count	= 0

	afe.periodic_measurement_start()

	while True:
		if afe.done:
			afe.done	= False
#			print( f"{count},  {afe.ch[ 0 ]} μV,  {afe.ch[ 1 ]} μV" )
			print( f"{afe.ch[ 0 ]:.3f},  {afe.ch[ 1 ]:.3f}" )
#			print( f"{afe.ch[ 0 ]},  {afe.ch[ 1 ]}" )
			count	+= 1

if __name__ == "__main__":
	main()
