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

use Config::Simple '-strict';
use CGI::Carp qw(fatalsToBrowser);
use CGI;
use LWP::UserAgent;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::JSON;
use Time::HiRes qw ( sleep );
use warnings;
use strict;
#use Data::Dumper;


##########################################################################
# Variables
##########################################################################

print STDERR "Nuki index.cgi called.\n";

# Read Form
my $cgi = CGI->new;
my $q = $cgi->Vars;

my $version = LoxBerry::System::pluginversion();
my $debug = 1;
my $template;

# Language Phrases
my %L;


# Globals 
my $localcallbackurl = "/plugins/".$lbpplugindir."/callback.php";
my $fullcallbackurl = "http://".lbhostname().":".lbwebserverport().$localcallbackurl;


##########################################################################
# AJAX
##########################################################################

# Prevent reading configs from others
system("chmod 0600 $lbpconfigdir/*.json");

if( $q->{ajax} ) {
	print STDERR "Ajax call: $q->{ajax}\n" if $debug;
	
	## Handle all ajax requests 
	require JSON;
	require Time::HiRes;
	my %response;
	ajax_header();
	
	# CheckSecPin
	if( $q->{ajax} eq "checksecpin" ) {
		print STDERR "CheckSecurePIN was called.\n" if $debug;
		$response{error} = &checksecpin();
		print JSON::encode_json(\%response);
	}

	# Save MQTT Settings
	if( $q->{ajax} eq "savemqtt" ) {
		print STDERR "savemqtt was called.\n" if $debug;
		$response{error} = &savemqtt();
		print JSON::encode_json(\%response);
	}
	
	# Search bridges
	if( $q->{ajax} eq "searchbridges" ) {
		print STDERR "Search for Bridges was called.\n" if $debug;
		$response{error} = &searchbridges();
		print JSON::encode_json(\%response);
	}
	
	# Delete bridges
	if( $q->{ajax} eq "deletebridge" ) {
		print STDERR "Delete Bridge was called.\n" if $debug;
		$response{error} = &deletebridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Add bridges
	if( $q->{ajax} eq "addbridge" ) {
		print STDERR "Add Bridge was called.\n" if $debug;
		%response = &addbridge();
		print JSON::encode_json(\%response);
	}
	
	# Activate bridges
	if( $q->{ajax} eq "activatebridge" ) {
		print STDERR "activatebridge was called.\n" if $debug;
		%response = &activatebridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Edit bridges
	if( $q->{ajax} eq "editbridge" ) {
		print STDERR "Edit Bridge was called.\n" if $debug;
		%response = &editbridge($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Checkonline Bridges
	if( $q->{ajax} eq "checkonline" ) {
		print STDERR "Checkonline was called.\n" if $debug;
		$response{online} = &checkonline($q->{url});
		print JSON::encode_json(\%response);
	}

	# Checktoken Bridges
	if( $q->{ajax} eq "checktoken" ) {
		print STDERR "Checktoken was called with Bridge ID " . $q->{bridgeid} . "\n" if $debug;
		%response = &checktoken($q->{bridgeid});
		print JSON::encode_json(\%response);
	}
	
	# Get single bridge config
	if( $q->{ajax} eq "getbridgeconfig" ) {
		print STDERR "Getbridgeconfig was called.\n" if $debug;
		if ( !$q->{bridgeid} ) {
			print STDERR "No bridge id given.\n" if $debug;
			$response{error} = "1";
			$response{message} = "No bridge id given";
		}
		elsif ( &checksecpin() ) {
			print STDERR "Wrong SecurePIN.\n" if $debug;
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
		print STDERR "Search for Devices was called.\n" if $debug;
		$response{error} = &searchdevices();
		print JSON::encode_json(\%response);
	}
	
	# Callback Management
	if( $q->{ajax} eq "callbacks" ) {
		print STDERR "Callbacks was called.\n" if $debug;
		$response{error} = callbacks();
		print JSON::encode_json(\%response);
	}
	
	
	# Get config
	if( $q->{ajax} eq "getconfig" ) {
		print STDERR "Getconfig was called.\n" if $debug;
		my $content;
		if ( !$q->{config} ) {
			print STDERR "No config given.\n" if $debug;
			$response{error} = "1";
			$response{message} = "No config given";
		}
		elsif ( &checksecpin() ) {
			print STDERR "Wrong SecurePIN.\n" if $debug;
			$response{error} = "1";
			$response{message} = "Wrong SecurePIN";
		}
		elsif ( !-e $lbpconfigdir . "/" . $q->{config} . ".json" ) {
			print STDERR "Config file does not exist.\n" if $debug;
			$response{error} = "1";
			$response{message} = "Config file does not exist";
		}
		else {
			# Config
			my $cfgfile = $lbpconfigdir . "/" . $q->{config} . ".json";
			print STDERR "Parsing Config: " . $cfgfile . "\n";
			$content = LoxBerry::System::read_file("$cfgfile");
			print $content;
		}
		print JSON::encode_json(\%response) if !$content;
	}
	
	exit;

	
##########################################################################
# Normal request (not AJAX)
##########################################################################

} else {
	
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
		print STDERR "The entered securepin is wrong.\n" if $debug;
		$error = 1;
	} else {
		print STDERR "You have entered the correct securepin. Continuing.\n" if $debug;
		$error = 0;
	}
	return ($error);
}

sub searchbridges
{
	my $ua = LWP::UserAgent->new(timeout => 10);
	print STDERR "Call https://api.nuki.io/discover/bridges\n";
	my $response = $ua->get('https://api.nuki.io/discover/bridges');
	my $errors;

	if ($response->is_success) {
		print STDERR "Success: " . $response->status_line . "\n";
		print STDERR "Response: " . $response->decoded_content . "\n" if $debug;
		my $jsonobjbr = LoxBerry::JSON->new();
		my $bridges = $jsonobjbr->parse($response->decoded_content);
		if ( !$bridges->{errorCode} && $bridges->{errorCode} ne "0" ) {$bridges->{errorCode} = "Undef"};
		print STDERR "ErrorCode: $bridges->{errorCode}\n" if $debug;
		if ($bridges->{errorCode} eq "0") {
			# Config
			my $cfgfile = $lbpconfigdir . "/bridges.json";
			my $jsonobj = LoxBerry::JSON->new();
			my $cfg = $jsonobj->open(filename => $cfgfile);
			for my $results( @{$bridges->{bridges}} ){
				print STDERR "Found BridgeID: " . $results->{bridgeId} . "\n" if $debug;
				if ( $cfg->{$results->{bridgeId}} ) {
					print STDERR "Bridge already exists in Config -> Skipping\n" if $debug;
					next;
				} else {
					print STDERR "Bridge does not exist in Config -> Saving\n" if $debug;
					$cfg->{$results->{bridgeId}}->{bridgeId} = $results->{bridgeId};
					$cfg->{$results->{bridgeId}}->{ip} = $results->{ip};
					$cfg->{$results->{bridgeId}}->{port} = $results->{port};
				}
			}
			$jsonobj->write();
		} else {
			print STDERR "Data Failure - Error Code: " . $bridges->{errorCode} . "\n";
			$errors++;
		}
	}
	else {
		print STDERR "Get Failure: " . $response->status_line . "\n";
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
		print STDERR "No Bridge ID given.\n";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		print STDERR "Editing Bridge data for $bridgeid.\n";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			print STDERR "Found Bridge: Saving new data.\n";
			$cfg->{$bridgeid}->{ip} = $q->{bridgeip};
			$cfg->{$bridgeid}->{port} = $q->{bridgeport};
			$cfg->{$bridgeid}->{token} = $q->{bridgetoken};
			$jsonobj->write();
			$response{error} = 0;
			$response{message} = "Bridge saved successfully.";
		} else {
			print STDERR "Bridge does not exist.\n";
			$response{error} = 1;
			$response{message} = "Bridge does not exist.";
		}
	}
	return (%response);
}

sub addbridge
{
	my %response;
	print STDERR "Add new Bridge.\n";
	if (!$q->{bridgeid}) {
		print STDERR "No BridgeID given.\n";
		$response{error} = 1;
		$response{message} = "No BridgeID given.";
	} else {
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$q->{bridgeid}}) {
			print STDERR "Bridge already exists.\n";
			$response{error} = 1;
			$response{message} = "Bridge already exists.";
		} else {
			$cfg->{$q->{bridgeid}}->{bridgeId} = $q->{bridgeid};
			$cfg->{$q->{bridgeid}}->{ip} = $q->{bridgeip};
			$cfg->{$q->{bridgeid}}->{port} = $q->{bridgeport};
			$cfg->{$q->{bridgeid}}->{token} = $q->{bridgetoken};
			$jsonobj->write();
			$response{error} = 0;
			$response{message} = "New Bridge saved successfully.";
		}
	}
	return (%response);
}

sub activatebridge
{
	my $bridgeid = $_[0];
	my %response;
	if (!$bridgeid) {
		print STDERR "No Bridge ID given.\n" if $debug;
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		print STDERR "Reading config for Bridge $bridgeid.\n" if $debug;
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			print STDERR "Found Bridge: Try to auth.\n" if $debug;
			# Auth
			my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/auth";
			print STDERR "Call Auth Command: $bridgeurl\n" if $debug;
			my $ua = LWP::UserAgent->new(timeout => 32);
			my $response = $ua->get("$bridgeurl");
			if ($response->code eq "200") {
				print STDERR "Received answer fron bridge\n" if $debug;
				my $jsonobjgetdev = LoxBerry::JSON->new();
				my $resp = $jsonobjgetdev->parse($response->decoded_content);
				if ($resp->{success}) {
					print STDERR "Success: " . $resp->{success} . "\n" if $debug;
					print STDERR "Token is: " . $resp->{token} . "\n" if $debug;
					$response{auth} = 1;
					$response{message} = "Auth successfull";
					$cfg->{$bridgeid}->{token} = $resp->{token};
					$jsonobj->write();
				} else {
					print STDERR "Auth Command failed or timed out\n" if $debug;
					$response{message} = "Auth Command failed or timed out";
				}
			} else {
				$response{auth} = 0;
				print STDERR "Auth Command failed\n" if $debug;
				$response{message} = "Auth Command failed";
			}
		} else {
			print STDERR "Bridge does not exist.\n" if $debug;
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
		print STDERR "No Bridge ID given.\n";
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		print STDERR "Reading config for Bridge $bridgeid.\n";
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			print STDERR "Found Bridge: Reading data.\n";
			$response{ip} = $cfg->{$bridgeid}->{ip};
			$response{port} = $cfg->{$bridgeid}->{port};
			$response{token} = $cfg->{$bridgeid}->{token};
			$response{error} = 0;
			$response{message} = "Bridge data read successfully.";
		} else {
			print STDERR "Bridge does not exist.\n";
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
		print STDERR "No Bridge ID given.\n" if $debug;
		$response{error} = 1;
		$response{message} = "No Bridge ID given.";
	} else {
		print STDERR "Reading config for Bridge $bridgeid.\n" if $debug;
		my $cfgfile = $lbpconfigdir . "/bridges.json";
		my $jsonobj = LoxBerry::JSON->new();
		my $cfg = $jsonobj->open(filename => $cfgfile);
		if ($cfg->{$bridgeid}) {
			print STDERR "Found Bridge: Check token.\n" if $debug;
			# Check online status
			my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/info?token=" . $cfg->{$bridgeid}->{token};
			print STDERR "Check Auth Status: $bridgeurl\n" if $debug;
			my $ua = LWP::UserAgent->new(timeout => 10);
			my $response = $ua->get("$bridgeurl");
			if ($response->code eq "200") {
				$response{auth} = 1;
			} else {
				$response{auth} = 0;
			}
		} else {
			print STDERR "Bridge does not exist.\n" if $debug;
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
	# Check online status
	my $bridgeurl = "http://" . $url . "/info";
	print STDERR "Check Online Status: $bridgeurl\n" if $debug;
	my $ua = LWP::UserAgent->new(timeout => 10);
	my $response = $ua->get("$bridgeurl");
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
		print STDERR "Parsing devices from Bridge " . $cfg->{$key}->{bridgeId} . "\n" if $debug;
		if (!$cfg->{$key}->{token}) {
			print STDERR "No token in config - skipping.\n" if $debug;
			next;
		} else {
			# Getting devices of Bridge
			my $bridgeid = $cfg->{$key}->{bridgeId};
			my $bridgeurl = "http://" . $cfg->{$bridgeid}->{ip} . ":" . $cfg->{$bridgeid}->{port} . "/list?token=" . $cfg->{$bridgeid}->{token};
			my $ua = LWP::UserAgent->new(timeout => 10);
			my $response = $ua->get("$bridgeurl");
			if ($response->code eq "200") {
				print STDERR "Authenticated successfully.\n" if $debug;
			} else {
				print STDERR "Authentication failed - skipping.\n" if $debug;
				next;
			}
			my $jsonobjgetdev = LoxBerry::JSON->new();
			my $devices = $jsonobjgetdev->parse($response->decoded_content);
			
			# Parsing Devices
			for my $results( @{$devices} ){
				print STDERR "Found Device: " . $results->{nukiId} . "\n" if $debug;
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


sub callbacks
{
	my $cfgfiledev = $lbpconfigdir . "/bridges.json";
	my $jsonobjdev = LoxBerry::JSON->new();
	my $cfgdev = $jsonobjdev->open(filename => $cfgfiledev, readonly => 1);
	if(!$cfgdev) {
		print STDERR "callbacks: Could not open $cfgfiledev - not configured yet?\n" if $debug;
		return;
	}
	
	# Walk through configured bridges
	
	my $bridgeloopsmax = 5;
	my %bridgeloops;
	
	foreach my $key (keys %$cfgdev) {
		
		# If any of the requests loop, we skip it
		$bridgeloops{$key}++;
		if( $bridgeloops{$key} > $bridgeloopsmax) {
			print STDERR "callbacks: Skipping bridge $key after $bridgeloopsmax retries\n";
			last;
		};
		
		print STDERR "callbacks: Parsing devices from Bridge " . $key . "\n" if $debug;
		if (!$cfgdev->{$key}->{token}) {
			print STDERR "callbacks: Bridge $key - No token in config, skipping.\n" if $debug;
			next;
		}
		
		my $callbacks = callback_list($cfgdev->{$key});
		
		if (!$callbacks) {
			print STDERR "callbacks: No callbacks for $cfgdev->{$key}\n" if $debug;
			callback_add($cfgdev->{$key}, $fullcallbackurl);
			redo;
		}
		
		my $checkresult = callback_fuzzycheck($cfgdev->{$key}, $callbacks);
		if( $checkresult == -1 ) {
			# Callbacks removed
			print STDERR "callbacks: A callback was removed - re-checking " . $cfgdev->{$key}->{bridgeId} . "\n" if $debug;
			redo;
		} elsif ( $checkresult == 1 ) {
			# Callback ok
			print STDERR "callbacks: Callback of " . $cfgdev->{$key}->{bridgeId} . " ok\n" if $debug;
			next;
		} else {
			# Callback missing
			print STDERR "callbacks: callback missing and will be added for " . $cfgdev->{$key}->{bridgeId} . "\n" if $debug;
			callback_add($cfgdev->{$key}, $fullcallbackurl);
			redo;
		}
	
	}

}


# Requests the callback list from a given bridgeobj
sub callback_list
{
	my ($bridgeobj) = @_;
	
	print STDERR "callback_list: Querying callbacks for ".$bridgeobj->{bridgeId}."\n" if $debug;
	sleep 0.1;
	
	my $bridgeid = $bridgeobj->{bridgeId};
	my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/list?token=" . $bridgeobj->{token};
	my $ua = LWP::UserAgent->new(timeout => 20);
	my $response = $ua->get("$bridgeurl");
	if ($response->code ne "200") {
		print STDERR "callback_list: Could not query callback list\n" if $debug;
		return;
	}
	
	# Parse response
	my $jsonobj_callback_list = LoxBerry::JSON->new();
	my $callbacks = $jsonobj_callback_list->parse($response->decoded_content);
	print STDERR "callback_list: Response: ".$response->decoded_content."\n";
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
	
	#use Data::Dumper;
	#print STDERR Dumper($callbacks);
	#print ref($callbacks->{callbacks})."\n";
	
	foreach my $callback ( @{$callbacks->{callbacks}} ) {
		print STDERR "callback_fuzzycheck: Checking for duplicates $callback->{url}\n" if $debug;
		next unless $checkduplicates{$callback->{url}}++;
		print STDERR "callback_fuzzycheck: URL $callback->{url} is a duplicate\n";
		callback_remove($bridgeobj, $callback->{id});
		$itemsremoved++;
		last;
	}
	
	# If duplicate callbacks were removed, we need to re-run the query for callbacks
	if($itemsremoved) {
		print STDERR "callback_fuzzycheck: Items were removed - return -1\n" if $debug;
		return -1;
	}
	
	my $callbackok = 0;
	foreach my $callback ( @{$callbacks->{callbacks}} ) {
		if($callback->{url} eq $fullcallbackurl) {
			print STDERR "callback_fuzzycheck: Callback exists\n" if $debug;
			$callbackok++;
			last;
		}
	}
	
	if($callbackok > 0) {
		print STDERR "callback_fuzzycheck: Callback exists - return 1\n" if $debug;
		return 1;
	}
	print STDERR "callback_fuzzycheck: Callback does not exist - return 0\n" if $debug;
	return 0;

}

# Removes a callback by it's id
# IMPORTANT: id of all callbacks may change on remove of an id. It is necessary to re-read the callback list after removal
# Returns:	1 ........ success
#			undef .... error
sub callback_remove
{
	my ($bridgeobj, $delid) = @_;
	
	if(!$bridgeobj or !$delid) {
		return undef;
	}
	
	print STDERR "callback_remove: Called for ".$bridgeobj->{bridgeId}." and callback id $delid\n" if $debug;
	sleep 0.1;
	
	my $bridgeid = $bridgeobj->{bridgeId};
	my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/remove?id=" . $delid . "&token=" . $bridgeobj->{token};
	print STDERR "callback_remove: Request $bridgeurl\n" if $debug;
	my $ua = LWP::UserAgent->new(timeout => 30);
	my $response = $ua->get("$bridgeurl");
	if ($response->code ne "200") {
		print STDERR "callback_remove: Error removing callback url with id $delid: $response->code $response->decoded_content\n" if $debug;
		return;
	}
	
	# Parse response
	my $jsonobj_callback_success = LoxBerry::JSON->new();
	my $success = $jsonobj_callback_success->parse($response->decoded_content);
	
	if( is_enabled($success->{success}) ) {
		return 1;
	}
	print STDERR "callback_remove: Error '" . $success->{message} . "' after removing callback urlid $delid\n" if $debug;
	return undef;
}


# Registers a new callback
# Returns:	1 ........ success
#			undef .... error
sub callback_add
{
	my ($bridgeobj, $callbackurl) = @_;
	
	print STDERR "callback_add: Adding callback for " . $bridgeobj->{bridgeId} . "\n" if $debug;
	sleep 0.1;
	
	if(!$bridgeobj or !$callbackurl) {
		print STDERR "callback_add: Missing parameters\n" if $debug;
		return undef;
	}
		
	# URL-Encode callback url
	my $callbackurl_enc = URI::Escape::uri_escape($callbackurl);
		
	my $bridgeid = $bridgeobj->{bridgeId};
	my $bridgeurl = "http://" . $bridgeobj->{ip} . ":" . $bridgeobj->{port} . "/callback/add?url=" . $callbackurl_enc . "&token=" . $bridgeobj->{token};
	print STDERR "callback_add: add request: $bridgeurl\n" if $debug;
	my $ua = LWP::UserAgent->new(timeout => 30);
	my $response = $ua->get("$bridgeurl");
	if ($response->code ne "200") {
		if( $response->code eq "400" ) {
			print STDERR "callback_add: Error adding callback url. Error 'URL invalid or too long': Callbackurl: $callbackurl_enc\n" if $debug;
		} elsif( $response->code eq "401" ) {
			print STDERR "callback_add: Error adding callback url. Token invalid\n" if $debug;
		} else {
			print STDERR "callback_add: Unknown error adding callback url $callbackurl_enc HTTP ".$response->code." ".$response->decoded_content."\n" if $debug;
		}
		return;
	}
	
	# Parse response
	my $jsonobj_callback_success = LoxBerry::JSON->new();
	my $success = $jsonobj_callback_success->parse($response->decoded_content);
	
	if( is_enabled($success->{success}) ) {
		return 1;
	}
	print STDERR "callback_add: Error '" . $success->{message} . "' after adding callback url $callbackurl_enc\n" if $debug;
	return undef;
}


sub savemqtt
{
	my $errors;
	my $cfgfile = $lbpconfigdir . "/mqtt.json";
	my $jsonobj = LoxBerry::JSON->new();
	my $cfg = $jsonobj->open(filename => $cfgfile);
	$cfg->{topic} = $q->{topic};
	$cfg->{server} = $q->{server};
	$cfg->{port} = $q->{port};
	$cfg->{username} = $q->{username};
	$cfg->{password} = $q->{password};
	$jsonobj->write();
	return ($errors);
}
