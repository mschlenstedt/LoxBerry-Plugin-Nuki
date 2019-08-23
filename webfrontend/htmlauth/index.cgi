#!/usr/bin/perl

# Copyright 2019 Michael Schlenstedt, michael@loxberry.de
#                Christian Fenzl, christian@loxberry.de
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

# use Config::Simple '-strict';
# use CGI::Carp qw(fatalsToBrowser);
use CGI;
use LoxBerry::System;
# use LoxBerry::Web;
# use LoxBerry::JSON; # Available with LoxBerry 2.0
require "$lbpbindir/libs/LoxBerry/JSON.pm";
use LoxBerry::Log;
use Time::HiRes qw ( sleep );
use warnings;
use strict;
#use Data::Dumper;

##########################################################################
# Variables
##########################################################################

my $log;

# Read Form
my $cgi = CGI->new;
my $q = $cgi->Vars;

my $version = LoxBerry::System::pluginversion();
my $template;

# Language Phrases
my %L;

# Globals 
my $lbhostname = lbhostname();
my $lbip = LoxBerry::System::get_localip();
my $lbaddress;
system ("host $lbhostname > /dev/null 2>&1");
if ($?) {
	$lbaddress = $lbip;
} else {
	$lbaddress = $lbhostname;
}
my $localcallbackurl = "/plugins/".$lbpplugindir."/callback.php";
my $fullcallbackurl = "http://".$lbaddress.":".lbwebserverport().$localcallbackurl;
my $nuki_locking_file = "/run/shm/{$lbpplugindir}_api_lock.lck";
my $cfgfiledev = $lbpconfigdir . "/bridges.json";
my $glob_lbuid;

##########################################################################
# AJAX
##########################################################################

# Prevent reading configs from others
system("chmod 0600 $lbpconfigdir/*.json");

if( $q->{ajax} ) {
	
	## Logging for ajax requests
	$log = LoxBerry::Log->new (
		name => 'AJAX',
		filename => "$lbplogdir/ajax.log",
		stderr => 1,
		loglevel => 7,
		addtime => 1,
		append => 1,
		nosession => 1,
	);
	
	LOGSTART "Ajax call: $q->{ajax}";
	LOGINF "LoxBerry network address is: $lbaddress";
	
	## Handle all ajax requests 
	require JSON;
	# require Time::HiRes;
	my %response;
	ajax_header();
	
	# CheckSecPin
	if( $q->{ajax} eq "checksecpin" ) {
		LOGINF "checksecpin: CheckSecurePIN was called.";
		$response{error} = &checksecpin();
		print JSON::encode_json(\%response);
	}

	# Save MQTT Settings
	if( $q->{ajax} eq "savemqtt" ) {
		LOGINF "savemqtt: savemqtt was called.";
		$response{error} = &savemqtt();
		print JSON::encode_json(\%response);
	}
	
	# Search bridges
	if( $q->{ajax} eq "searchbridges" ) {
		LOGINF "searchbridges: Search for Bridges was called.";
		$response{error} = &searchbridges();
		print JSON::encode_json(\%response);
	}
	
	# Delete bridges
	if( $q->{ajax} eq "deletebridge" ) {
		LOGINF "deletebridge: Delete Bridge was called.";
		$response{error} = &deletebridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Add bridges
	if( $q->{ajax} eq "addbridge" ) {
		LOGINF "addbridge: Add Bridge was called.";
		%response = &addbridge();
		print JSON::encode_json(\%response);
	}
	
	# Activate bridges
	if( $q->{ajax} eq "activatebridge" ) {
		LOGINF "activatebridge: activatebridge was called.";
		%response = &activatebridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Edit bridges
	if( $q->{ajax} eq "editbridge" ) {
		LOGINF "editbridge: Edit Bridge was called.";
		%response = &editbridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Checkonline Bridges
	if( $q->{ajax} eq "checkonline" ) {
		LOGINF "checkonline: Checkonline was called.";
		$response{online} = &checkonline($q->{url});
		print JSON::encode_json(\%response);
	}

	# Checktoken Bridges
	if( $q->{ajax} eq "checktoken" ) {
		LOGINF "checktoken: Checktoken was called with Bridge ID " . $q->{bridgeid} . "";
		%response = &checktoken($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Get single bridge config
	if( $q->{ajax} eq "getbridgeconfig" ) {
		LOGINF "getbridgeconfig: was called.";
		if ( !$q->{bridgeid} ) {
			LOGINF "getbridgeconfig: No bridge id given.";
			$response{error} = "1";
			$response{message} = "No bridge id given";
		}
		elsif ( &checksecpin() ) {
			LOGINF "getbridgeconfig: Wrong SecurePIN.";
			$response{error} = "1";
			$response{message} = "Wrong SecurePIN";
		}
		else {
			# Get config
			%response = &getbridgeconfig ( $q->{bridgeid} );
		}
		print JSON::encode_json(\%response);
	}
	
	# Search Devices
	if( $q->{ajax} eq "searchdevices" ) {
		LOGINF "searchdevices: Search for Devices was called.";
		$response{error} = &searchdevices();
		print JSON::encode_json(\%response);
	}
	
	# Manage callbacks of ALL bridges
	if( $q->{ajax} eq "callbacks" ) {
		LOGINF "callbacks: Callbacks was called.";
		$response{error} = callbacks();
		print JSON::encode_json(\%response);
	}
	
	# Manage callbacks of a SINGLE bridge
	if( $q->{ajax} eq "callback" ) {
		LOGINF "callback: Callback was called.";
		($response{error}, $response{message}) = callback($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Manage callbacks of a SINGLE bridge
	if( $q->{ajax} eq "callback_remove_all_from_all" ) {
		LOGINF "callback_remove_all_from_all: Remove all Callbacks from all bridges was called.";
		callback_remove_all_from_all();
		print JSON::encode_json(\%response);
	}
	
	# Get config
	if( $q->{ajax} eq "getconfig" ) {
		LOGINF "getconfig: Getconfig was called.";
		my $content;
		if ( !$q->{config} ) {
			LOGINF "getconfig: No config given.";
			$response{error} = "1";
			$response{message} = "No config given";
		}
		elsif ( &checksecpin() ) {
			LOGINF "getconfig: Wrong SecurePIN.";
			$response{error} = "1";
			$response{message} = "Wrong SecurePIN";
		}
		elsif ( !-e $lbpconfigdir . "/" . $q->{config} . ".json" ) {
			LOGINF "getconfig: Config file does not exist.";
			$response{error} = "1";
			$response{message} = "Config file does not exist";
		}
		else {
			# Config
			my $cfgfile = $lbpconfigdir . "/" . $q->{config} . ".json";
			LOGINF "Parsing Config: " . $cfgfile;
			$content = LoxBerry::System::read_file("$cfgfile");
			print $content;
		}
		print JSON::encode_json(\%response) if !$content;
	}
	
	exit;

##########################################################################
# CRONJOB operation
##########################################################################

} elsif ( is_enabled($q->{cron}) ) {

	## Logging for cronjob requests
	$log = LoxBerry::Log->new (
		name => 'Cronjob',
		stderr => 1,
		loglevel => 7,
		addtime => 1,
	);
	
	LOGSTART "Cronjob operation";
	LOGINF "Starting callback maintenance";
	callbacks();
	exit;

	
##########################################################################
# Normal request (not AJAX)
##########################################################################

} else {
	
	require LoxBerry::Web;
	
	## Logging for serverside webif requests
	$log = LoxBerry::Log->new (
		name => 'Webinterface',
		filename => "$lbplogdir/webinterface.log",
		stderr => 1,
		loglevel => 7,
		addtime => 1
	);

	LOGSTART "Nuki WebIf";
	
	# Init Template
	$template = HTML::Template->new(
	    filename => "$lbptemplatedir/settings.html",
	    global_vars => 1,
	    loop_context_vars => 1,
	    die_on_bad_params => 0,
	);
	%L = LoxBerry::System::readlanguage($template, "language.ini");
	
	# Default is Bridges form
	$q->{form} = "bridges" if !$q->{form};

	if ($q->{form} eq "bridges") { &form_bridges() }
	elsif ($q->{form} eq "devices") { &form_devices() }
	elsif ($q->{form} eq "mqtt") { &form_mqtt() };

	# Print the form
	&form_print();
}

exit;


##########################################################################
# Form: BRIDGES
##########################################################################

sub form_bridges
{
	$template->param("FORM_BRIDGES", 1);
	return();
}


##########################################################################
# Form: DEVICES
##########################################################################

sub form_devices
{
	$template->param("FORM_DEVICES", 1);
	return();
}

##########################################################################
# Form: MQTT
##########################################################################

sub form_mqtt
{
	$template->param("FORM_MQTT", 1);
	my $mqttplugindata = LoxBerry::System::plugindata("mqttgateway");
	$template->param("MQTTGATEWAY_INSTALLED", 1) if($mqttplugindata);
	return();
}


##########################################################################
# Print Form
##########################################################################

sub form_print
{
	# Navbar
	our %navbar;

	$navbar{1}{Name} = "$L{'COMMON.LABEL_BRIDGES'}";
	$navbar{1}{URL} = 'index.cgi?form=bridges';
	$navbar{1}{active} = 1 if $q->{form} eq "bridges";
	
	$navbar{2}{Name} = "$L{'COMMON.LABEL_DEVICES'}";
	$navbar{2}{URL} = 'index.cgi?form=devices';
	$navbar{2}{active} = 1 if $q->{form} eq "devices";
	
	$navbar{3}{Name} = "$L{'COMMON.LABEL_MQTT'}";
	$navbar{3}{URL} = 'index.cgi?form=mqtt';
	$navbar{3}{active} = 1 if $q->{form} eq "mqtt";
	
	$navbar{4}{Name} = "$L{'COMMON.LABEL_TEMPLATEBUILDER'}";
	$navbar{4}{URL} = 'index.cgi?form=templatebuilder';
	$navbar{4}{URL} = "/admin/plugins/$lbpplugindir/templatebuilder.cgi";
	$navbar{4}{target} = '_blank';
	
	$navbar{5}{Name} = "$L{'COMMON.LABEL_LOG'}";
	$navbar{5}{URL} = LoxBerry::Web::loglist_url();
	$navbar{5}{target} = '_blank';
	
	# Template
	LoxBerry::Web::lbheader($L{'COMMON.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "");
	print $template->output();
	LoxBerry::Web::lbfooter();
	
	exit;

}


######################################################################
# AJAX functions
######################################################################

sub ajax_header
{
	print $cgi->header(
			-type => 'application/json',
			-charset => 'utf-8',
			-status => '200 OK',
	);	
}	

sub checksecpin
{
	my $error;
	if ( LoxBerry::System::check_securepin($q->{secpin}) ) {
		LOGINF "checksecpin: The entered securepin is wrong.";
		$error = 1;
	} else {
		LOGINF "checksecpin: You have entered the correct securepin. Continuing.";
		$error = 0;
	}
	return ($error);
}

sub searchbridges
{
	require LWP::UserAgent;

	my $ua = LWP::UserAgent->new(timeout => 10);
	LOGINF "searchbridges: Call https://api.nuki.io/discover/bridges\n";
	my $response = $ua->get('https://api.nuki.io/discover/bridges');
	my $errors;

	if ($response->is_success) {
		LOGINF "searchbridges: Success: " . $response->status_line . "\n";
		LOGINF "searchbridges: Response: " . $response->decoded_content . "";
		my $jsonobjbr = LoxBerry::JSON->new();
		my $bridges = $jsonobjbr->parse($response->decoded_content);
		if ( !$bridges->{errorCode} && $bridges->{errorCode} ne "0" ) {$bridges->{errorCode} = "Undef"};
		LOGINF "searchbridges: ErrorCode: $bridges->{errorCode}";
		if ($bridges->{errorCode} eq "0") {
			# Config
			my $cfgfile = $lbpconfigdir . "/bridges.json";
			my $jsonobj = LoxBerry::JSON->new();
			my $cfg = $jsonobj->open(filename => $cfgfile);
			for my $results( @{$bridges->{bridges}} ){
				LOGINF "searchbridges: Found BridgeID: " . $results->{bridgeId} . "";
				if ( $cfg->{$results->{discoveryBridgeId}} ) {
					LOGINF "searchbridges: Bridge already exists in Config -> Skipping";
					next;
				} else {
					LOGINF "searchbridges: Bridge does not exist in Config -> Saving";
					$cfg->{$results->{bridgeId}}->{discoveryBridgeId} = $results->{bridgeId};
					$cfg->{$results->{bridgeId}}->{intBridgeId} = $results->{bridgeId};
					$cfg->{$results->{bridgeId}}->{bridgeId} = "";
					$cfg->{$results->{bridgeId}}->{ip} = $results->{ip};
					$cfg->{$results->{bridgeId}}->{port} = $results->{port};
					
				}
			}
			$jsonobj->write();
		} else {
			LOGINF "searchbridges: Data Failure - Error Code: " . $bridges->{errorCode} . "\n";
			$errors++;
		}
	}
	else {
		LOGINF "searchbridges: Get Failure: " . $response->status_line . "\n";
		$errors++;
	}
	return ($errors);
}

sub deletebridge
{
	my $bridgeid = $_[0];
	my $errors;
	if (!$bridgeid) {
		$errors++;
	} else {
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		delete $cfg->{$bridgeid};
		$jsonobj->write();
	}
	return ($errors);
}

sub editbridge
{
	my $bridgeid = $_[0];
	my %response;
	if (!$bridgeid) {
		LOGINF "editbridge: No Bridge ID given.\n";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		LOGINF "editbridge: Editing Bridge data for $bridgeid.\n";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			LOGINF "editbridge: Found Bridge: Saving new data.\n";
			$cfg->{$bridgeid}->{ip} = $q->{bridgeip};
			$cfg->{$bridgeid}->{port} = $q->{bridgeport};
			$cfg->{$bridgeid}->{token} = $q->{bridgetoken};
			$jsonobj->write();
			$response{error} = 0;
			$response{message} = "Bridge saved successfully.";
			# Check Callbacks
			my ($cberror, $cbmessage) = callback( $bridgeid );
			$response{message} = $response{message} . " / " . $cbmessage;
			if ( $cberror ) {
				$response{error} = 1;
			}
		} else {
			LOGINF "editbridge: Bridge does not exist.\n";
			$response{error} = 1;
			$response{message} = "Bridge does not exist.";
		}
	}
	return (%response);
}

sub addbridge
{
	my %response;
	
	if (!$q->{bridgeid}) {
	# Generate random internal bridge id (intBridgeId)
		$q->{bridgeid} = "9" . int(rand(999999999));
	}
	
	LOGINF "addbridge: Add new Bridge.\n";
	# if (!$q->{bridgeid}) {
		# LOGINF "addbridge: No BridgeID given.\n";
		# $response{error} = 1;
		# $response{message} = "No BridgeID given.";
	# } else {
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$q->{bridgeid}}) {
			LOGINF "addbridge: Bridge already exists.\n";
			$response{error} = 1;
			$response{message} = "Bridge already exists.";
		} else {
			$cfg->{$q->{bridgeid}}->{bridgeId} = "";
			$cfg->{$q->{bridgeid}}->{discoveryBridgeId} = "";
			$cfg->{$q->{bridgeid}}->{intBridgeId} = $q->{bridgeid};
			
			$cfg->{$q->{bridgeid}}->{ip} = $q->{bridgeip};
			$cfg->{$q->{bridgeid}}->{port} = $q->{bridgeport};
			$cfg->{$q->{bridgeid}}->{token} = $q->{bridgetoken};
			$jsonobj->write();
			$response{error} = 0;
			$response{message} = "New Bridge saved successfully.";
			# Check Callbacks
			my ($cberror, $cbmessage) = callback( $q->{bridgeid} );
			$response{message} = $response{message} . " / " . $cbmessage;
			if ( $cberror ) {
				$response{error} = 1;
			}
		}
	# }
	return (%response);
}

sub activatebridge
{
	my $bridgeid = $_[0];
	my %response;
	if (!$bridgeid) {
		LOGINF "activatebridge: No Bridge ID given.";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		LOGINF "activatebridge: Reading config for Bridge $bridgeid.";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			LOGINF "activatebridge: Found Bridge: Try to auth.";
			# Auth
			# my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/auth";
			# LOGINF "activatebridge: Call Auth Command: $bridgeurl";
			# my $ua = LWP::UserAgent->new(timeout => 32);
			# my $response = $ua->get("$bridgeurl");
			
			my $response = api_call(
				ip 	=> $cfg->{$bridgeid}->{ip},
				port	=> $cfg->{$bridgeid}->{port},
				apiurl	=> '/auth',
				timeout	=> 32
			);
			
			
			if ($response->code eq "200") {
				LOGINF "activatebridge: Received answer fron bridge";
				my $jsonobjgetdev = LoxBerry::JSON->new();
				my $resp = $jsonobjgetdev->parse($response->decoded_content);
				if ($resp->{success}) {
					LOGINF "activatebridge: Success: " . $resp->{success} . "";
					LOGINF "activatebridge: Token is: " . $resp->{token} . "";
					$response{auth} = 1;
					$response{message} = "Auth successfull";
					$cfg->{$bridgeid}->{token} = $resp->{token};
					$jsonobj->write();
					# Check Callbacks
					my ($cberror, $cbmessage) = callback( $bridgeid );
					$response{message} = $response{message} . " / " . $cbmessage;
					if ( $cberror ) {
						$response{error} = 1;
						$response{auth} = 0;
					}
				} else {
					LOGINF "activatebridge: Auth Command failed or timed out";
					$response{message} = "Auth Command failed or timed out";
				}
			} else {
				$response{auth} = 0;
				LOGINF "activatebridge: Auth Command failed";
				$response{message} = "Auth Command failed";
			}
		} else {
			LOGINF "activatebridge: Bridge does not exist.";
			$response{error} = 1;
			$response{message} = "Bridge does not exist.";
		}
	}
	return (%response);
}

sub getbridgeconfig
{
	my $bridgeid = $_[0];
	my %response;
	if (!$bridgeid) {
		LOGINF "getbridgeconfig: No Bridge ID given.\n";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		LOGINF "getbridgeconfig: Reading config for Bridge $bridgeid.\n";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			LOGINF "getbridgeconfig: Found Bridge: Reading data.\n";
			$response{ip} = $cfg->{$bridgeid}->{ip};
			$response{port} = $cfg->{$bridgeid}->{port};
			$response{token} = $cfg->{$bridgeid}->{token};
			$response{error} = 0;
			$response{message} = "Bridge data read successfully.";
		} else {
			LOGINF "getbridgeconfig: Bridge does not exist.\n";
			$response{error} = 1;
			$response{message} = "Bridge does not exist.";
		}
	}
	return (%response);
}

sub checktoken
{
	my $bridgeid = $_[0];
	my %response;
	if (!$bridgeid) {
		LOGINF "checktoken: No Bridge ID given.";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		LOGINF "checktoken: Reading config for Bridge $bridgeid.";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			LOGINF "checktoken: Found Bridge: Check token.";
			# Check online status
			#my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/info?token=" . $cfg->{$bridgeid}->{token};
			#LOGINF "checktoken: Check Auth Status: $bridgeurl";
			#my $ua = LWP::UserAgent->new(timeout => 10);
			#my $response = $ua->get("$bridgeurl");
			
			my $response = api_call(
				ip 		=> $cfg->{$bridgeid}->{ip},
				port	=> $cfg->{$bridgeid}->{port},
				apiurl	=> '/info',
				token	=> $cfg->{$bridgeid}->{token}
			);
			
			if ($response->code eq "200") {
				$response{auth} = 1;
				my $info_data;
				eval {
					$info_data = json_decode( $response->decoded_content );
					$cfg->{$bridgeid}->{bridgeId} = $info_data->{ids}->{hardwareId} if (defined $info_data->{ids}->{hardwareId});
					$cfg->{$bridgeid}->{discoveryBridgeId} = $info_data->{ids}->{serverId} if (defined $info_data->{ids}->{serverId});
					$jsonobj->write;
				};
				if($@) { 
					LOGERR "checktoken: /info response processing failed: $@";
				}
				
			} else {
				$response{auth} = 0;
			}
		} else {
			LOGINF "checktoken: Bridge does not exist.";
			$response{error} = 1;
			$response{message} = "Bridge does not exist.";
		}
	}
	return (%response);
}

sub checkonline
{
	my $url = $_[0];
	my $online;
	
	my ($host, $port) = split(':', $url, 2);
	
	# Check online status
	#my $bridgeurl = "http://" . $url . "/info";
	# LOGINF "checkonline: Check Online Status: $bridgeurl";
	# my $ua = LWP::UserAgent->new(timeout => 10);
	# my $response = $ua->get("$bridgeurl");
	
	my $response = api_call(
				ip 		=> $host,
				port	=> $port,
				apiurl	=> '/info',
			);
	
	
	if ($response->code eq "401") {
		$online++;
	}
	return ($online);
}

sub searchdevices
{
	my $errors;
	# Devices config
	my $cfgfiledev = $lbpconfigdir . "/devices.json";
	unlink ( $cfgfiledev );
	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev);
	# Bridges config
	my $cfgfile = $lbpconfigdir . "/bridges.json";
	my $jsonobj = LoxBerry::JSON->new();
	my $cfg = $jsonobj->open(filename => $cfgfile);
	# Parsing Bridges
	foreach my $key (keys %$cfg) {
		LOGINF "searchdevices: Parsing devices from Bridge " . $cfg->{$key};
		if (!$cfg->{$key}->{token}) {
			LOGINF "searchdevices: No token in config - skipping.";
			next;
		} else {
			# Getting devices of Bridge
			my $bridgeid = $key;
			# my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/list?token=" . $cfg->{$bridgeid}->{token};
			# my $ua = LWP::UserAgent->new(timeout => 10);
			# my $response = $ua->get("$bridgeurl");
			
			my $response = api_call(
				ip 		=> $cfg->{$bridgeid}->{ip},
				port	=> $cfg->{$bridgeid}->{port},
				apiurl	=> '/list',
				token	=> $cfg->{$bridgeid}->{token}
			);
			
			if ($response->code eq "200") {
				LOGINF "searchdevices: Authenticated successfully.";
			} else {
				LOGINF "searchdevices: Authentication failed - skipping.";
				next;
			}
			my $jsonobjgetdev = LoxBerry::JSON->new();
			my $devices = $jsonobjgetdev->parse($response->decoded_content);
			
			# Parsing Devices
			for my $results( @{$devices} ){
				LOGINF "searchdevices: Found Device: " . $results->{nukiId} . "";
				$cfgdev->{$results->{nukiId}}->{nukiId} = $results->{nukiId};
				$cfgdev->{$results->{nukiId}}->{bridgeId} = $bridgeid;
				$cfgdev->{$results->{nukiId}}->{name} = $results->{name};
				$cfgdev->{$results->{nukiId}}->{deviceType} = $results->{deviceType};
			}
			$jsonobjdev->write();
		}	
	}
	return ($errors);
}

#####################################################################
## Callback routines
#####################################################################

sub callbacks
{
	
	
	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev, readonly => 1);
	if(!$cfgdev) {
		LOGINF "callbacks: Could not open $cfgfiledev - not configured yet?";
		return;
	}
	
	# Walk through configured bridges
	
	foreach my $key (keys %$cfgdev) {
		callback($key);
	}
	return undef;
}

# Manages the callbacks of ONE specific bridge
# Input: bridgeid
# Response: 0 error, 1 ok
sub callback
{
	
	my ($bridgeid) = @_;

	my $bridgeloopsmax = 5;
	my %bridgeloops;
	my $bridgeerrors=0;
	my $bridgemsg;

	
	if(!$bridgeid) {
		$bridgeerrors++;
		$bridgemsg = "callback: Parameter bridgeid missing";
		LOGERR $bridgemsg;
		return ($bridgeerrors, $bridgemsg);
	}
	
	my $lbuid = callback_lbuid_get_from_file();

	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev, readonly => 1);



	# Don't wonder, this is a loop
	{
		# If any of the requests loop, we skip it
		$bridgeloops{$bridgeid}++;
		if( $bridgeloops{$bridgeid} > $bridgeloopsmax) {
			$bridgemsg = "callback: Skipping bridge $bridgeid after $bridgeloopsmax retries";
			LOGERR $bridgemsg;
			$bridgeerrors++;
			next;
		};
		
		LOGINF "callback: Parsing devices from Bridge " . $bridgeid . "";
		if (!$cfgdev->{$bridgeid}->{token}) {
			$bridgemsg = "callback: Bridge $bridgeid - No token in config, skipping.";
			LOGERR $bridgemsg;
			$bridgeerrors++;
			next;
		}
		
		my $callbacks = callback_list($cfgdev->{$bridgeid});
		
		if (!$callbacks) {
			LOGINF "callback: No callbacks for $cfgdev->{$bridgeid}";
			callback_add($cfgdev->{$bridgeid}, $fullcallbackurl."?lbuid=".$lbuid);
			redo;
		}
		
		my $checkresult = callback_fuzzycheck($cfgdev->{$bridgeid}, $callbacks);
		if( $checkresult == -1 ) {
			# Callbacks removed
			LOGINF "callback: A callback was removed - re-checking " . $bridgeid;
			redo;
		} elsif ( $checkresult == 1 ) {
			# Callback ok
			$bridgemsg = "callback: Callback of " . $bridgeid . " ok";
			LOGINF $bridgemsg;
			next;
		} else {
			# Callback missing
			LOGINF "callback: callback missing and will be added for " . $bridgeid;
			callback_add($cfgdev->{$bridgeid}, $fullcallbackurl."?lbuid=".$lbuid);
			redo;
		}
	}
	return ($bridgeerrors, $bridgemsg);
}

# Requests the callback list from a given bridgeobj
sub callback_list
{
	my ($bridgeobj) = @_;
	
	LOGINF "callback_list: Querying callbacks for ".$bridgeobj->{intBridgeId}."";
	
	# my $bridgeid = $bridgeobj->{bridgeId};
	# my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/list?token=" . $bridgeobj->{token};
	# my $ua = LWP::UserAgent->new(timeout => 20);
	# my $response = $ua->get("$bridgeurl");
	
	my $response = api_call(
				ip 		=> $bridgeobj->{ip},
				port	=> $bridgeobj->{port},
				apiurl	=> '/callback/list',
				token	=> $bridgeobj->{token},
	);
	
	if ($response->code ne "200") {
		LOGINF "callback_list: Could not query callback list";
		return;
	}
	
	# Parse response
	my $jsonobj_callback_list = LoxBerry::JSON->new();
	my $callbacks = $jsonobj_callback_list->parse($response->decoded_content);
	LOGINF "callback_list: Response: ".$response->decoded_content."\n";
	return $callbacks;

}

# Checks the callbacks for consistency
# Returns: 	-1 .... Duplicates removed - caller should redo the check
# 			 0 .... No callback found
#			 1 .... Callback ok
sub callback_fuzzycheck
{
	my ($bridgeobj, $callbacks) = @_;
	
	my $callback_exists = 0;
	
	return undef if (!$callbacks);
	
	my %checkduplicates;
	my $itemsremoved = 0;
	my $lbuid = callback_lbuid_get_from_file();
	
	#use Data::Dumper;
	#print STDERR Dumper($callbacks);
	#print ref($callbacks->{callbacks})."\n";
	
	# Check for and remove duplicates
	foreach my $callback ( @{$callbacks->{callbacks}} ) {
		LOGINF "callback_fuzzycheck: Checking for duplicates $callback->{url}";
		next unless $checkduplicates{$callback->{url}}++;
		LOGINF "callback_fuzzycheck: URL $callback->{url} is a duplicate\n";
		callback_remove($bridgeobj, $callback->{id});
		$itemsremoved++;
		last;
	}
	
	# If duplicate callbacks were removed, we need to re-run the query for callbacks
	if($itemsremoved) {
		LOGINF "callback_fuzzycheck: Items were removed - return -1";
		return -1;
	}
	
	my $callbackok = 0;
	foreach my $callback ( @{$callbacks->{callbacks}} ) {
				
		## Detection for changed ip/hostname/port
		# Split url (https://stackoverflow.com/a/26766402/3466839)
		$callback->{url} =~ /^(([^:\/?#]+):)?(\/\/([^\/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?/;
		my $hostpart = $4 ? $4 : ""; 		# loxberry-dev.brunnenweg.lan:80 
		my $pathpart = $5 ? $5 : "";		# /plugins/nukismartlock/callback.php
		my $parampart = $7 ? $7 : "";		# lbuid=1234
		
		if( $hostpart eq $lbaddress.":".lbwebserverport() and $pathpart eq $localcallbackurl and $parampart eq "lbuid=".$lbuid ) {
			LOGINF "callback_fuzzycheck: Callback exists";
			$callbackok++;
			next;
		}

		# Remove plugin callbacks without lbuid
		if($pathpart eq "/plugins/$lbpplugindir/callback.php" and !$parampart) {
			LOGINF "callback_fuzzycheck: Callback without lbuid will be removed - return -1";
			callback_remove($bridgeobj, $callback->{id});
			return -1;
		}
		
		# Skip callbacks from other LoxBerry's
		if($pathpart eq "/plugins/$lbpplugindir/callback.php" and $parampart ne "lbuid=".$lbuid) {
			LOGINF "callback_fuzzycheck: Callback from other LoxBerry skipped";
			next;
		}

		# Skip third-party callbacks
		if($pathpart ne "/plugins/$lbpplugindir/callback.php") {
			LOGDEB "callback_fuzzycheck: Callback $callback->{url} skipped - not from this plugin";
			next;
		}
		
		# Now we have found a callback from the plugin, but with different hostname/ip
		LOGINF "callback_fuzzycheck: Callback with different hostname/ip will be removed - return -1";
		callback_remove($bridgeobj, $callback->{id});
		return -1;
		
	}
	
	if($callbackok > 0) {
		LOGINF "callback_fuzzycheck: Callback exists - return 1";
		return 1;
	}
	LOGINF "callback_fuzzycheck: Callback does not exist - return 0";
	return 0;

}

# Removes a callback by it's id
# IMPORTANT: id of all callbacks may change on remove of an id. It is necessary to re-read the callback list after removal
# Returns:	1 ........ success
#			undef .... error
sub callback_remove
{
	my ($bridgeobj, $delid) = @_;
	
	if(!$bridgeobj or ! defined $delid) {
		return undef;
	}
	
	LOGINF "callback_remove: Called for ".$bridgeobj->{intBridgeId}." and callback id $delid";
	
	# my $bridgeid = $bridgeobj->{bridgeId};
	# my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/remove?id=" . $delid . "&token=" . $bridgeobj->{token};
	# LOGINF "callback_remove: Request $bridgeurl";
	# my $ua = LWP::UserAgent->new(timeout => 30);
	# my $response = $ua->get("$bridgeurl");
	
	my $response = api_call(
				ip 		=> $bridgeobj->{ip},
				port	=> $bridgeobj->{port},
				apiurl	=> '/callback/remove',
				timeout	=> 30,
				token	=> $bridgeobj->{token},
				params	=> "id=" . $delid,
	);
	
	if ($response->code ne "200") {
		LOGINF "callback_remove: Error removing callback url with id $delid: $response->code $response->decoded_content";
		return;
	}
	
	# Parse response
	my $jsonobj_callback_success = LoxBerry::JSON->new();
	my $success = $jsonobj_callback_success->parse($response->decoded_content);
	
	if( is_enabled($success->{success}) ) {
		return 1;
	}
	LOGINF "callback_remove: Error '" . $success->{message} . "' after removing callback urlid $delid";
	return undef;
}

# This removes ALL callbacks (also foreign) from a specific bridgeId
# Input: bridgeid
# Returns: undef
sub callback_remove_all_from_bridge 
{

	my ($bridgeid) = @_;

	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev, readonly => 1);
	
	if( defined $cfgdev->{$bridgeid} and $cfgdev->{$bridgeid}->{token} ) {
		callback_remove( $cfgdev->{$bridgeid}, "2" );
		callback_remove( $cfgdev->{$bridgeid}, "1" );
		callback_remove( $cfgdev->{$bridgeid}, "0" );
	} else {
		LOGCRIT "BridgeId not known, or no token defined";
	}
}

# This removes ALL callbacks (also foreign) from ALL bridges
# Input: nothing
# Returns: nothing
sub callback_remove_all_from_all {

	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev, readonly => 1);
	
	foreach my $bridgeid (keys %$cfgdev) {
		callback_remove_all_from_bridge($bridgeid);
	}
}

# Registers a new callback
# Returns:	1 ........ success
#			undef .... error
sub callback_add
{
	my ($bridgeobj, $callbackurl) = @_;
	
	LOGINF "callback_add: Adding callback for " . $bridgeobj->{intBridgeId} . "";
	
	if(!$bridgeobj or !$callbackurl) {
		LOGINF "callback_add: Missing parameters";
		return undef;
	}
		
	# URL-Encode callback url
	my $callbackurl_enc = URI::Escape::uri_escape($callbackurl);
		
	# my $bridgeid = $bridgeobj->{bridgeId};
	# my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/add?url=" . $callbackurl_enc . "&token=" . $bridgeobj->{token};
	# LOGINF "callback_add: add request: $bridgeurl";
	# my $ua = LWP::UserAgent->new(timeout => 30);
	# my $response = $ua->get("$bridgeurl");
	
	my $response = api_call(
				ip 		=> $bridgeobj->{ip},
				port	=> $bridgeobj->{port},
				apiurl	=> '/callback/add',
				timeout	=> 30,
				token	=> $bridgeobj->{token},
				params	=> "url=" . $callbackurl_enc,
	);
	
	if ($response->code ne "200") {
		if( $response->code eq "400" ) {
			LOGINF "callback_add: Error adding callback url. Error 'URL invalid or too long': Callbackurl: $callbackurl_enc";
		} elsif( $response->code eq "401" ) {
			LOGINF "callback_add: Error adding callback url. Token invalid";
		} else {
			LOGINF "callback_add: Unknown error adding callback url $callbackurl_enc HTTP ".$response->code." ".$response->decoded_content."";
		}
		return;
	}
	
	# Parse response
	my $jsonobj_callback_success = LoxBerry::JSON->new();
	my $success = $jsonobj_callback_success->parse($response->decoded_content);
	
	if( is_enabled($success->{success}) ) {
		return 1;
	}
	LOGINF "callback_add: Error '" . $success->{message} . "' after adding callback url $callbackurl_enc";
	return undef;
}

sub callback_lbuid_get_from_file
{
	if($glob_lbuid) {
		return $glob_lbuid;
	}
	
	my $loxberryidfile = "$lbsconfigdir/loxberryid.cfg";
	my $glob_lbuid="12345";
	if( ! -e $loxberryidfile) {
		LOGERR "callback_lbuid_get_from_file: $loxberryidfile does not exist, returning $glob_lbuid";
		return $glob_lbuid;
	}
	my $realloxberryid = LoxBerry::System::read_file($loxberryidfile);
	if( length($realloxberryid) < 11)  {
		LOGERR "callback_lbuid_get_from_file: $loxberryidfile content seems to be invalid, returning $glob_lbuid";
		return $glob_lbuid;
	}
	$glob_lbuid = substr $realloxberryid, 5, 5;
	return $glob_lbuid;
}

##########################################################################
# NUKI API Calls
# Use named parameters:
# 	ip 
#	port
#	apiurl (e.g. /auth)
#	token (leave empty if this is a non-token request)
# 	params (this are the params for the apicall, without token)
#	timeout (default is 10)
# Returns:
#	http response object
##########################################################################

sub api_call
{
	
	my %p = @_;
	my $errors = 0;

	LOGINF "api_call $p{apiurl}: Called";
	
	# Default values
	$p{timeout} = defined $p{timeout} ? $p{timeout} : 10;
	
	# Verify parts
	if(!$p{ip}) {
		LOGERR "api_call: ip missing";
		$errors++;
	}
	if(!$p{port}) {
		LOGERR "api_call: port missing";
		$errors++;
	}
	if(!$p{apiurl}) {
		LOGERR "api_call: apiurl missing";
		$errors++;
	}
	if(!$p{token}) {
		LOGINF "api_call: Unsecured request without token";
	}

	if($errors != 0) {
		LOGCRIT "api_call: Mandatory parameters missing. Returning undef";
		return undef;
	}
	
	# Check for running api call
	my $fh = api_call_lock();
	
	require LWP::UserAgent;
	
	my $ua = LWP::UserAgent->new(timeout => $p{timeout});
	
	# Build request url
	
	my @request;
	
	push @request, "http://";
	push @request, $p{ip}, ":", $p{port};
	push @request, $p{apiurl};
	if($p{params}) {
		push @request, "?", $p{params};
	}
	if($p{token}) {
		if($p{params}) {
			push @request, "&";
		} else {
			push @request, "?";
		}
		push @request, "token=".$p{token};
	}
	
	my $url = join "", @request;
	LOGDEB "api_call: Calling request url: $url";
	my $response = $ua->get($url);
	
	if ($response->code eq "401") {
		LOGERR "api_call: HTTP 401 - The request token is invalid";
		LOGERR "api_call: Response: " . $response->decoded_content if ($response->decoded_content);
	}
	
	api_call_unlock($fh);
	
	return $response;

}

sub api_call_lock
{

	CORE::open(my $fh, '>', $nuki_locking_file);
	my $starttime = Time::HiRes::gettimeofday();
	my $lockstate;
	while ( !$lockstate or Time::HiRes::gettimeofday() > ($starttime+20) ) {
		$lockstate = flock($fh, 2);
		if (!$lockstate) {
			LOGINF "api_call_lock: Waiting for file lock since " . sprintf("%.2f", Time::HiRes::gettimeofday()-$starttime) . " seconds...";
			Time::HiRes::sleep(0.05);
		}
	}
	if ( !$lockstate ) {
		LOGERR "api_call_lock: Could not get exclusive lock after " . sprintf("%.2f", Time::HiRes::gettimeofday()-$starttime) . " seconds";
		return undef;
	} else {
		LOGOK "api_call_lock: Exclusive lock set after " . sprintf("%.2f", Time::HiRes::gettimeofday()-$starttime) . " seconds";
	}
	Time::HiRes::sleep(0.05);
	return $fh;

}

sub api_call_unlock
{
	my $fh = shift;

	my $unlock = CORE::close($fh);
	LOGOK "api_call_unlock: call_api closed/unlocked" if ($unlock);
	LOGERR "api_call_unlock: Could not close/unlock" if (!$unlock);
	
}

####################################################################

sub savemqtt
{
	my $errors;
	my $cfgfile = $lbpconfigdir . "/mqtt.json";
	my $jsonobj = LoxBerry::JSON->new();
	my $cfg = $jsonobj->open(filename => $cfgfile);
	$cfg->{topic} = $q->{topic};
	$cfg->{usemqttgateway} = $q->{usemqttgateway};
	$cfg->{server} = $q->{server};
	$cfg->{port} = $q->{port};
	$cfg->{username} = $q->{username};
	$cfg->{password} = $q->{password};
	$jsonobj->write();
	return ($errors);
}


END {
	if($log) {
		LOGEND;
	}
}

