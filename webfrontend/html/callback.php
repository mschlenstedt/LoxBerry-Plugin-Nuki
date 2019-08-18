<?php

	$brokeraddress = "localhost:1883";
	$brokeruser = "loxberry";
	$brokerpass = "passwort";
	define( "TOPIC", "nuki/");

	require_once "./phpMQTT/phpMQTT.php";

	echo "Data received:\n";
	$json = file_get_contents('php://input');
	echo $json;
	error_log("DATA: " . $json);
	$nukidata = json_decode($json);
	if (!empty($nukidata)) {
		mqtt_publish( [ $nukidata->nukiId => $json ] );
	}
	






####################################################
# MQTT handler
####################################################
function mqtt_publish ( $keysandvalues ) {
	
	global $brokeraddress, $brokeruser, $brokerpass;
	
	$broker = explode(':', $brokeraddress, 2);
	$broker[1] = !empty($broker[1]) ? $broker[1] : 1883;
	
	$client_id = uniqid(gethostname()."_nuki");
	$mqtt = new Bluerhinos\phpMQTT($broker[0],  $broker[1], $client_id);
	if( $mqtt->connect(true, NULL, $brokeruser, $brokerpass) ) {
		foreach ($keysandvalues as $key => $value) {
			$mqtt->publish(TOPIC . "$key", $value, 0, 1);
		}
		$mqtt->close();
	}
}




?>

