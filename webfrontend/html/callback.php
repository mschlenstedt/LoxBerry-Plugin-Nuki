<?php

	require_once "loxberry_system.php";
	require_once "loxberry_log.php";
	require_once "./phpMQTT/phpMQTT.php";
	
	$params = [
		"name" => "Callback",
		"filename" => LBPLOGDIR."/callback.log",
		"append" => 1,
		"stdout" => 1,
		"addtime" => 1,
		"loglevel" => 6
	];
	$log = LBLog::newLog ($params);
	LOGSTART("Callback log");

	$SentByType = array (
		1 => "callback",
		2 => "cron",
		3 => "manual",
		254 => "testing"
	);
	
	$mqttcfgfile = LBPCONFIGDIR."/mqtt.json";
	
	tolog("LOGINF", "Callback processing"); 
	
	if( $argc > 1 ) {
		$longopts = array(
			"json:",
			"sentbytype:",
		);
		$options = getopt(null, $longopts);
		if( empty($options["json"]) or empty($options["sentbytype"]) ) {
			echo "--json and --sentbytype parameters required\n";
			exit(1);
		}
		$options["json"] = stripslashes ( $options["json"] );
		
	} else {
		$options["json"] = file_get_contents('php://input');
		$options["sentbytype"] = 1;
	}
	
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
	echo "Type : " . $SentByType[$options["sentbytype"]] . " (" . $options["sentbytype"] . ")\n";
	
	echo "DATA : {$options["json"]}\n";


	$nukidata = json_decode($options["json"]);
	if ( !empty($nukidata) and isset($nukidata->nukiId) ) {
		echo "OK: Publishing...\n";
		mqtt_publish( [ 
			$nukidata->nukiId => $options["json"], 
			$nukidata->nukiId."/sentBy" => $options["sentbytype"],
			$nukidata->nukiId."/sentByName" => $SentByType[$options["sentbytype"]],
			$nukidata->nukiId."/sentAtTimeLox" => epoch2lox(),
			$nukidata->nukiId."/sentAtTimeISO" => currtime(),
			] );
			tolog("LOGOK", "Published: " . $nukidata->nukiId . " sentByName " . $SentByType[$options["sentbytype"]] . " Data\n" . $options["json"]);
	} else {
		tolog("LOGCRIT", "No valid json data");
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

	// Creates a log object, automatically assigned to your plugin, with the group name "PHPLog"
	$logfunction($message);
}


// Shutdown handler

register_shutdown_function('shutdown');

function shutdown() 
{
	LOGEND();
}


?>

