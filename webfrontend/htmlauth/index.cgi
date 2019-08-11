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
#use JSON qw( decode_json );
use LoxBerry::System;
use LoxBerry::Web;
#use MIME::Base64;
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

##########################################################################
# AJAX
##########################################################################

if( $q->{ajax} ) {
	print STDERR "Ajax call: $q->{ajax}\n";
	
	## Handle all ajax requests 
	require JSON;
	require Time::HiRes;
	my %response;
	ajax_header();
	
	# CheckSecPin
	if( $q->{ajax} eq "checksecpin" ) {
	print STDERR "CheckSecurePIN was called.";
		if ( LoxBerry::System::check_securepin($q->{secpin}) ) {
			print STDERR "The entered securepin is wrong.";
			$response{message} = "The entered securepin is wrong.";
			$response{error} = 1;
		} else {
			print STDERR "You have entered the correct securepin. Continuing.";
			$response{message} = "You have entered the correct securepin. Continuing.";
			$response{error} = 0;
		}
		print JSON::encode_json(\%response);
	}
	
	exit;

##########################################################################
# Main program
##########################################################################

} else {

}

##########################################################################
# Main program
##########################################################################

# Template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/settings.html",
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

# Language
my %L = LoxBerry::System::readlanguage($template, "language.ini");

# Navbar
our %navbar;
$navbar{1}{Name} = "$L{'COMMON.LABEL_BRIDGES'}";
$navbar{1}{URL} = 'index.cgi?form=bridges';

$navbar{2}{Name} = "$L{'COMMON.LABEL_SMARTLOCKS'}";
$navbar{2}{URL} = 'index.cgi?form=smartlocks';

$navbar{3}{Name} = "$L{'COMMON.LABEL_MQTT'}";
$navbar{3}{URL} = 'index.cgi?form=mqtt';

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
