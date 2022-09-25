from	machine		import	Pin, I2C
from	utime		import	sleep
from	nxp_periph	import	PCT2075

def main():
	i2c			= I2C( 0, freq = (400 * 1000) )
	temp_sensor	= PCT2075( i2c )

	while True:
		value	= temp_sensor.read()
		print( value )
		sleep( 1 )

if __name__ == "__main__":
	main()
