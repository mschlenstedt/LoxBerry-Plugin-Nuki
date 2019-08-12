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
use warnings;
use strict;

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


##########################################################################
# AJAX
##########################################################################

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
	
	# Search bridges
	if( $q->{ajax} eq "searchbridges" ) {
		print STDERR "Search for Bridges was called.\n" if $debug;
		$response{error} = &searchbridges();;
		print JSON::encode_json(\%response);
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
	elsif ($q->{form} eq "smartlocks") { &form_smartlocks() }
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

	# Config
	my $cfgfile = $lbpconfigdir . "/bridges.json";
	print STDERR "Parsing Config: " . $cfgfile . "\n";
	my $jsonobj = LoxBerry::JSON->new();
	my $cfg = $jsonobj->open(filename => $cfgfile);
	my @bridges;
	foreach my $key (keys %$cfg) {
		print STDERR "Found Bridge: " . $cfg->{$key}->{bridgeId} . "\n";
		my %bridge;
		%bridge = (
			'BRIDGEID' => $cfg->{$key}->{bridgeId},
			'IP' => $cfg->{$key}->{ip},
			'PORT' => $cfg->{$key}->{port},
			'TOKEN' => $cfg->{$key}->{token},
		);
		# Check online status
		my $bridgeurl = "http://" . $cfg->{$key}->{ip} . ":" . $cfg->{$key}->{port} . "/info";
		print STDERR "Check Online Status: $bridgeurl\n";
		my $ua = LWP::UserAgent->new(timeout => 10);
		my $response = $ua->get("$bridgeurl");
		if ($response->code eq "401") {
			$bridge{STATUS} = "<span style='color:green'>$L{'BRIDGES.LABEL_ONLINE'}</span>";
		} else {
			$bridge{STATUS} = "<span style='font-weight:bold; color:red'>$L{'BRIDGES.LABEL_OFFLINE'}</span>";
		}
		# Check discovery status
		if ( is_enabled($cfg->{$key}->{discovery}) ) {
			$bridge{DISCOVERY} = $L{'BRIDGES.LABEL_ENABLED'};
		} else {
			$bridge{DISCOVERY} = $L{'BRIDGES.LABEL_DISABLED'};
		}

		push(@bridges, \%bridge);
	}
	$template->param("BRIDGES" => \@bridges);
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
	
	$navbar{2}{Name} = "$L{'COMMON.LABEL_SMARTLOCKS'}";
	$navbar{2}{URL} = 'index.cgi?form=smartlocks';
	$navbar{2}{active} = 1 if $q->{form} eq "smartlocks";
	
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
	LoxBerry::Web::lbheader($L{'SETTINGS.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "");
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
					if ( $results->{ip} eq "0.0.0.0" ) {
						$cfg->{$results->{bridgeId}}->{discovery} = "disabled";
					} else {
						$cfg->{$results->{bridgeId}}->{discovery} = "enabled";
					}
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
