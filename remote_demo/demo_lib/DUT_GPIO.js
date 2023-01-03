/****************************
 ****	register controls
 ****************************/
 
/******** updateRegField ********/

function updateRegField( idx ) {
	let valueFieldElement = document.getElementById( "regField" + idx );
	let value	= parseInt( valueFieldElement.value, 16 );
	let no_submit	= 0;
	
	if ( isNaN( value ) ) {
		no_submit	= 1;
		value = document.getElementById( "Slider" + idx ).value;
	}
	value	= (value < 0  ) ?   0 : value;
	value	= (255 < value) ? 255 : value;
	valueFieldElement.value = hex( value );

	if ( no_submit )
		return;

	let url	= REQ_HEADER + "reg=" + idx + "&val=" + value;
	ajaxUpdate( url )
}


let prev_reg	= [];	//	to prevent refresh on user writing field

function allRegLoad() {
	let url	= REQ_HEADER + 'allreg='
	ajaxUpdate( url, function (){
		let obj = JSON.parse( this.responseText );

		for ( let i = 0; i < obj.reg.length; i++ ) {
			let value	= obj.reg[ i ];
			if ( value != prev_reg[ i ] ) {
				document.getElementById('regField' + i ).value	= hex( value );
			}
		}
		prev_reg	= obj.reg;
	} );
}

function singleReload() {
	allRegLoad();
}

let	intervalTimer;
function autoReload() {
	intervalTimer	= setInterval( allRegLoad, 200 );
}

function stopReload() {
	clearInterval( intervalTimer );
}

window.addEventListener('load', function () {
	allRegLoad();
});
