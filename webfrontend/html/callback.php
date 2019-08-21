<?php

	require_once "loxberry_system.php";
	require_once "./phpMQTT/phpMQTT.php";
		
	$mqttcfgfile = LBPCONFIGDIR."/mqtt.json";
	$json = file_get_contents('php://input');
		
	// Read MQTT config from plugin config
	$mqttcfg = json_decode(file_get_contents($mqttcfgfile));
	if( empty($mqttcfg) ) {
		tolog("LOGCRIT", "MQTT config $mqttcfgfile is empty or invalid. Check your MQTT settings.");
		exit(1);
	}
	
	// Topic
	$topic = !empty($mqttcfg->topic) ? $mqttcfg->topic : "nuki";
	if( substr($topic, -1) != "/" ) {
		$topic = $topic."/";
	}
	define( "TOPIC", $topic);

	// Broker
	if( is_enabled($mqttcfg->usemqttgateway) ) {
		// Use MQTT Gateway credentials
		// Check if MQTT plugin in installed
		$mqttplugindata = LBSystem::plugindata("mqttgateway");
		if( !empty($mqttplugindata) ) {
			$mqttconf = json_decode(file_get_contents(LBHOMEDIR . "/config/plugins/" . $mqttplugindata['PLUGINDB_FOLDER'] . "/mqtt.json" ));
			$mqttcred = json_decode(file_get_contents(LBHOMEDIR . "/config/plugins/" . $mqttplugindata['PLUGINDB_FOLDER'] . "/cred.json" ));
			$brokeraddress = $mqttconf->Main->brokeraddress;
			$brokeruser = $mqttcred->Credentials->brokeruser;
			$brokerpass = $mqttcred->Credentials->brokerpass;
			echo "Using broker settings from MQTT Gateway plugin:\n";
		}
	} else {
		// Use MQTT config from Nuki plugin
		$brokeraddress = $mqttcfg->server.":".$mqttcfg->port;
		$brokeruser = $mqttcfg->username;
		$brokerpass = $mqttcfg->password;
		echo "Using broker settings from NUKI plugin:\n";
	}
	
	// Broker validation
	@list($host, $port) = explode(":", $brokeraddress, 2);
	$port = $port ? $port : 1883;
	
	echo "Topic: ". TOPIC . "\n";
	echo "Host : $host\n";
	echo "Port : $port\n";
	echo "User : $brokeruser\n";
	echo "Pass : " . substr($brokerpass, 0, 1) . str_repeat("*", strlen($brokerpass)-1) . "\n";
	echo "POST : $json\n";


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
	} else {
		echo "MQTT connection failed\n";
		tolog("LOGCRIT", "Connection to MQTT broker failed ($broker[0]:$broker[1] User $brokeruser)");
	}
}


######################################################
# To log a single line to a LoxBerry log (for errors)
######################################################
function tolog ( $logfunction, $message ) {

	require_once "loxberry_log.php";
	// Creates a log object, automatically assigned to your plugin, with the group name "PHPLog"
	$params = [
		"name" => "Callback",
		"filename" => LBPLOGDIR."/callback.log",
		"append" => 1,
		"stdout" => 1
	];
	$log = LBLog::newLog ($params);
	LOGSTART("Callback log");
	$logfunction($message);
	LOGEND();
}




?>

