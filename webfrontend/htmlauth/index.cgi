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
use JSON qw( decode_json );
use LoxBerry::System;
use LoxBerry::Web;
use MIME::Base64;
use warnings;
#use strict;

##########################################################################
# Variables
##########################################################################

# Read Form
my $cgi = CGI->new;
$cgi->import_names('R');

##########################################################################
# Read Settings
##########################################################################

# Version of this script
my $version = LoxBerry::System::pluginversion();

# Settings
my $cfg = new Config::Simple("$lbpconfigdir/mirobot2lox.cfg");

#########################################################################
# Parameter
#########################################################################

my $error;

##########################################################################
# Main program
##########################################################################

# Template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/settings.html",
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
    associate => $cfg,
);

# Language
my %L = LoxBerry::Web::readlanguage($template, "language.ini");

# Save Form 1 
if ($R::saveformdata1) {
	
  	$template->param( FORMNO => '1' );

	# OK - now installing...

	# Write configuration file(s)
	$cfg->param("MAIN.SENDUDP", "$R::sendudp");
	$cfg->param("MAIN.UDPPORT", "$R::udpport");
	$cfg->param("MAIN.MS", "$R::ms");
	$cfg->param("MAIN.CRON", "$R::cron");
	$cfg->param("MAIN.GETDATA", "$R::getdata");

	for (my $i=1;$i<=5;$i++) {
		$cfg->param("ROBOT$i" . ".ACTIVE", ${"R::r$i" . "active"} );
		$cfg->param("ROBOT$i" . ".IP", ${"R::r$i" . "ip"} );
		$cfg->param("ROBOT$i" . ".TOKEN", ${"R::r$i" . "token"} );
		$cfg->param("ROBOT$i" . ".DOCKRELEASETIME", ${"R::r$i" . "dockreleasetime"} );
	}

	$cfg->save();
		
	# Create Cronjob
	open (F,">/tmp/$lbpplugindir.crontab");

	print F "SHELL=/bin/bash\n";
	print F "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n";
	print F "MAILTO=\"\"\n";
	print F "# minute hour day_of_month month day_of_week user command\n";

	if ( $R::getdata ) {
		if ( $R::cron eq "30" ) {
			print F "# Every 30 seconds\n";
			print F "* * * * * loxberry $lbpbindir/grabber.pl > /dev/null 2>&1\n";
			print F "* * * * * loxberry ( sleep 30; $lbpbindir/grabber.pl > /dev/null 2>&1 )\n";
		}
		if ( $R::cron eq "60" ) {
			print F "# Every 60 seconds\n";
			print F "* * * * * loxberry $lbpbindir/grabber.pl > /dev/null 2>&1\n";
		}
		if ( $R::cron eq "90" ) {
			print F "# Every 90 seconds\n";
			print F "*/3 * * * * loxberry $lbpbindir/grabber.pl > /dev/null 2>&1\n";
			print F "* * * * * loxberry ( sleep 90; $lbpbindir/grabber.pl > /dev/null 2>&1 )\n";
		}
		if ( $R::cron eq "120" ) {
			print F "# Every 120 seconds\n";
			print F "*/2 * * * * loxberry $lbpbindir/grabber.pl > /dev/null 2>&1\n";
		}
		if ( $R::cron eq "180" ) {
			print F "# Every 180 seconds\n";
			print F "*/3 * * * * loxberry $lbpbindir/grabber.pl > /dev/null 2>&1\n";
		}
	} 

	close(F);

	system ("sudo $lbssbindir/installcrontab.sh $lbpplugindir /tmp/$lbpplugindir.crontab >/dev/null 2>&1");
	unlink ("/tmp/$lbpplugindir.crontab");

	# Template output
	&save;

	exit;

}

# Install Soundpack - Step 1
if ($R::saveformdata3) {

	$template->param( "SOUNDPACK", $R::soundpack );
	$template->param( "ROBOT", $R::robot );
	&installsoundpack1;

}

# Install Soundpack - Step 2
if ($R::saveformdata4) {

	my $logfile = "/tmp/mirobosoundpackinstall.log";
	my $i = $R::robot;
	my $ip = $cfg->param( "ROBOT$i" . ".IP");
	my $token = $cfg->param( "ROBOT$i" . ".TOKEN");
	my $urlpkg = "https://raw.githubusercontent.com/mschlenstedt/MiRobot-Soundpacks/master/soundpacks/$R::soundpack" . ".pkg";
	my $urlmd5 = "https://raw.githubusercontent.com/mschlenstedt/MiRobot-Soundpacks/master/soundpacks/$R::soundpack" . ".md5";

	# Output template
	&installsoundpack2;

	# Without the following workaround
	# the script cannot be executed as
	# background process via CGI
	my $pid = fork();
	die "Fork failed: $!" if !defined $pid;

	if ($pid == 0) {

		#print "Content-Type: text/plain\n\n";

		# Grab MD5Sum
		#my $md5sum = `$bins->{CURL} --connect-timeout 10 --max-time 60 --retry 5 -LfksS $urlmd5 2>&1`;
		my $md5sum = `curl --connect-timeout 10 --max-time 60 --retry 5 -LfksS $urlmd5`;
		$md5sum =~ s/ .*//; # Sum ist vor 1. Leerzeichen

		# do this in the child
		open STDIN, "</dev/null";
		open STDOUT, ">$logfile";
		open STDERR, ">/dev/null";

		print "Command: mirobo --ip $ip --token $token install_sound $urlpkg $md5sum\n";
		print "Please be patient - may take some seconds... Wait until you see 'Installation of sid xxxx is complete!'.\n\n";

		# Do the installation
		system ("export LC_ALL=C.UTF-8; export LANG=C.UTF-8; mirobo --ip $ip --token $token install_sound $urlpkg $md5sum 2>&1");


	} # End Child process

	exit;

}

#
# Navbar
#

our %navbar;
$navbar{1}{Name} = "$L{'SETTINGS.LABEL_SETTINGS'}";
$navbar{1}{URL} = 'index.cgi?form=1';

$navbar{2}{Name} = "$L{'SETTINGS.LABEL_ROBOTCOMMANDS'}";
$navbar{2}{URL} = 'index.cgi?form=2';

$navbar{3}{Name} = "$L{'SETTINGS.LABEL_SOUNDPACKS'}";
$navbar{3}{URL} = 'index.cgi?form=3';

$navbar{4}{Name} = "$L{'SETTINGS.LABEL_TEMPLATEBUILDER'}";
$navbar{4}{URL} = 'index.cgi?form=4';
#$navbar{4}{URL} = "/admin/plugins/$lbpplugindir/templatebuilder.cgi";
#$navbar{4}{target} = '_blank';

$navbar{5}{Name} = "$L{'SETTINGS.LABEL_LOG'}";
$navbar{5}{URL} = LoxBerry::Web::loglist_url();
$navbar{5}{target} = '_blank';

#
# Menu: Settings
#

if ($R::form eq "1" || !$R::form) {

  $navbar{1}{active} = 1;
  $template->param( "FORM1", 1);

  my @values;
  my %labels;

  # GetData
  @values = ('0', '1' );
  %labels = (
        '0' => $L{'SETTINGS.LABEL_OFF'},
        '1' => $L{'SETTINGS.LABEL_ON'},
    );
  my $getdata = $cgi->popup_menu(
        -name    => 'getdata',
        -id      => 'getdata',
        -values  => \@values,
	-labels  => \%labels,
	-default => $cfg->param('MAIN.GETDATA'),
    );
  $template->param( GETDATA => $getdata );

  # Cron
  @values = ('30', '60', '90', '120', '180' );
  %labels = (
        '30' => $L{'SETTINGS.LABEL_30SECONDS'},
        '60' => $L{'SETTINGS.LABEL_60SECONDS'},
        '90' => $L{'SETTINGS.LABEL_90SECONDS'},
        '120' => $L{'SETTINGS.LABEL_120SECONDS'},
        '180' => $L{'SETTINGS.LABEL_180SECONDS'},
    );
  my $cron = $cgi->popup_menu(
        -name    => 'cron',
        -id      => 'cron',
        -values  => \@values,
	-labels  => \%labels,
	-default => $cfg->param('MAIN.CRON'),
    );
  $template->param( CRON => $cron );

  # Miniservers
  my $mshtml = LoxBerry::Web::mslist_select_html( 
	  FORMID => 'ms',
	  SELECTED => $cfg->param('MAIN.MS'),
	  DATA_MINI => 1,
	  LABEL => "",
  );
  $template->param('MS', $mshtml);

  # If a HTML::Template object is used, send the html to the template
  # $maintemplate->param('MSHTML', $mshtml);
  # SendUDP
  @values = ('0', '1' );
  %labels = (
        '0' => $L{'SETTINGS.LABEL_OFF'},
        '1' => $L{'SETTINGS.LABEL_ON'},
    );
  my $sendudp = $cgi->popup_menu(
        -name    => 'sendudp',
        -id      => 'sendudp',
        -values  => \@values,
	-labels  => \%labels,
	-default => $cfg->param('MAIN.SENDUDP'),
    );
  $template->param( SENDUDP => $sendudp );

  # Send HTML
  $template->param( "WEBSITE", "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/robotsdata.txt");

  # Robots
  $template->param( "SENDCMD", "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/sendcmd.cgi");

  my $form;
  for (my $i=1;$i<=5;$i++) {
	@values = ('0', '1' );
	%labels = (
		'0' => $L{'SETTINGS.LABEL_OFF'},
		'1' => $L{'SETTINGS.LABEL_ON'},
	);
	$form = $cgi->popup_menu(
		-name => "r" . $i . "active",
		-id => "r" . $i . "active",
		-values	=> \@values,
		-labels	=> \%labels,
		-default => $cfg->param( "ROBOT$i" . ".ACTIVE"),
	);
	if ( $cfg->param( "ROBOT$i" . ".ACTIVE") ) {
			$template->param( "R$i" . "COLLAPSED" => "data-collapsed='false'" );
	}
	$template->param( "R$i" . "ACTIVE" => $form );

  }

#
# Menu: Robot Commands
#

} elsif ($R::form eq "2") {

  $navbar{2}{active} = 1;
  $template->param( "FORM2", 1);
  $template->param( "SENDCMD", "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/sendcmd.cgi");
  $template->param( "DOCKRELEASETIME1", $cfg->param('ROBOT1.DOCKRELEASETIME')*1000);
  $template->param( "DOCKRELEASETIME2", $cfg->param('ROBOT2.DOCKRELEASETIME')*1000);
  $template->param( "DOCKRELEASETIME3", $cfg->param('ROBOT3.DOCKRELEASETIME')*1000);
  $template->param( "DOCKRELEASETIME4", $cfg->param('ROBOT4.DOCKRELEASETIME')*1000);
  $template->param( "DOCKRELEASETIME5", $cfg->param('ROBOT5.DOCKRELEASETIME')*1000);

#
# Menu: SoundPacks
#

} elsif ($R::form eq "3") {

  $navbar{3}{active} = 1;
  $template->param( "FORM3", 1);

  # Select Soundpacks
  @values = ('ca_gtts_male',
	  'ca_aws_female',
	  'ca_gtts_male',
	  'de_aws_female1',
	  'de_aws_female2',
	  'de_aws_male',
	  'de_gtts_female',
	  'en_aws_female',
	  'en_aws_male',
	  'en_gtts_female',
	  'es_aws_female',
	  'es_aws_male',
	  'es_gtts_female',
	  'fi_gtts_female',
	  'fr_aws_female',
	  'fr_aws_male',
	  'fr_gtts_female',
	  'pl_aws_female',
	  'pl_aws_male',
	  'pl_gtts_male',
	);
  %labels = (
	  'ca_aws_female' => 'CA: Amazon Polly Female ',
	  'ca_gtts_male' => 'CA: Google TTS Male',
	  'de_aws_female1' => 'DE: Amazon Polly Female 1',
	  'de_aws_female2' => 'DE: Amazon Polly Female 2',
	  'de_aws_male' => 'DE: Amazon Polly Male',
	  'de_gtts_female' => 'DE: Google TTS Female',
	  'en_aws_female' => 'EN: Amazon Polly Female',
	  'en_aws_male' => 'EN: Amazon Polly Male',
	  'en_gtts_female' => 'EN: Google TTS Female',
	  'es_aws_female' => 'ES: Amazon Polly Female',
	  'es_aws_male' => 'ES: Amazon Polly Male',
	  'es_gtts_female' => 'ES: Google TTS Female',
	  'fi_gtts_female' => 'FI: Google TTS Female',
	  'fr_aws_female' => 'FR: Amazon Polly Female',
	  'fr_aws_male' => 'FR: Amazon Polly Male',
	  'fr_gtts_female' => 'FR: Google TTS Female',
	  'pl_aws_female' => 'PL: Amazon Polly Female',
	  'pl_aws_male' => 'PL: Amazon Polly Male',
	  'pl_gtts_male' => 'PL: Google TTS Male',
    );
  my $soundpack = $cgi->popup_menu(
        -name    => 'soundpack',
        -id      => 'soundpack',
        -values  => \@values,
	-labels  => \%labels,
    );
  $template->param( SOUNDPACK => $soundpack );

  # Robots
  @values = ('1', '2', '3', '4', '5' );
  %labels = (
        '1' => $L{'SETTINGS.LABEL_MIROBOT'} . " 1",
        '2' => $L{'SETTINGS.LABEL_MIROBOT'} . " 2",
        '3' => $L{'SETTINGS.LABEL_MIROBOT'} . " 3",
        '4' => $L{'SETTINGS.LABEL_MIROBOT'} . " 4",
        '5' => $L{'SETTINGS.LABEL_MIROBOT'} . " 5",
    );
  my $robots = $cgi->popup_menu(
        -name    => 'robot',
        -id      => 'robot',
        -values  => \@values,
	-labels  => \%labels,
    );
  $template->param( ROBOTS => $robots );


#
# Menu: Inputs/Outputs
#

} elsif ($R::form eq "4") {

  $navbar{4}{active} = 1;
  $template->param( "FORM4", 1);


  # Create VOs
  my @robots;
  for (my $i=1;$i<=5;$i++) {
	if ( $cfg->param( "ROBOT$i" . ".ACTIVE") ) {
		my %robot;
		%robot = (
      		'NAME' => $L{'SETTINGS.LABEL_MIROBOT'} . " #$i",
      		'V_NAME' => $L{'SETTINGS.LABEL_MIROBOT'} . "$i",
      		'IP' => $cfg->param( "ROBOT$i" . ".IP"),
		'VIU_STATE' => "MiRobot$i state",
		'VIU_ERROR' => "MiRobot$i error",
		);

		my $virtualoutput = HTML::Template->new(
			filename => "$lbptemplatedir/virtualoutput.xml",
			global_vars => 1,
			loop_context_vars => 1,
			die_on_bad_params => 0,
			associate => $cfg,
		);
		$virtualoutput->param("VO_NAME" => $L{'SETTINGS.LABEL_MIROBOT'} . "$i" );
		$virtualoutput->param("VO_SENDCMD" => "http://$ENV{HTTP_HOST}");
		$virtualoutput->param("ROBOTNO" => $i );
		$virtualoutput->param("SENDCMD" => "/plugins/$lbpplugindir/sendcmd.cgi");

		my $voxml = encode_base64($virtualoutput->output);
		$robot{VO_URL} = "data:application/octet-stream;charset=utf-8;base64,$voxml";

		push(@robots, \%robot);
  		$template->param(ROWS => $i);
	}
  }
  $template->param(COUNTS => \@robots);

  # Create VIUs
  my @robots;
  for (my $i=1;$i<=5;$i++) {
	my %robot;
	%robot = (
      	'V_NAME' => $L{'SETTINGS.LABEL_MIROBOT'} . "$i",
	);
	push(@robots, \%robot);
  }

	my $virtualinput_http = HTML::Template->new(
		filename => "$lbptemplatedir/virtualinput_http.xml",
		global_vars => 1,
		loop_context_vars => 1,
		die_on_bad_params => 0,
		associate => $cfg,
	);

  $virtualinput_http->param(COUNTS => \@robots);
  $virtualinput_http->param(VIU_URL => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/robotsdata.txt");
  $viuhttpxml = encode_base64($virtualinput_http->output);
  $template->param(VIU_HTTP_URL => "data:application/octet-stream;charset=utf-8;base64,$viuhttpxml");

  my $virtualinput_udp = HTML::Template->new(
	filename => "$lbptemplatedir/virtualinput_udp.xml",
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params => 0,
	associate => $cfg,
	);

  $virtualinput_udp->param(COUNTS => \@robots);
  $viuudpxml = encode_base64($virtualinput_udp->output);
  $template->param(VIU_UDP_URL => "data:application/octet-stream;charset=utf-8;base64,$viuudpxml");

}


# Template
LoxBerry::Web::lbheader($L{'SETTINGS.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "");
print $template->output();
LoxBerry::Web::lbfooter();

exit;


#####################################################
# Install Soundpack
#####################################################

sub installsoundpack1
{
	$template->param( "INSTALLSOUNDPACK1", 1);
	LoxBerry::Web::lbheader($L{'SETTINGS.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "help.html");
	print $template->output();
	LoxBerry::Web::lbfooter();

	exit;
}

sub installsoundpack2
{
	$template->param( "INSTALLSOUNDPACK2", 1);
	LoxBerry::Web::lbheader($L{'SETTINGS.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "help.html");
	print $template->output();
	LoxBerry::Web::lbfooter();

	return(); # Do not exit here!
}

#####################################################
# Save
#####################################################

sub save
{
	$template->param( "SAVE", 1);
	LoxBerry::Web::lbheader($L{'SETTINGS.LABEL_PLUGINTITLE'} . " V$version", "https://www.loxwiki.eu/display/LOXBERRY/MiRobot2Lox-NG", "help.html");
	print $template->output();
	LoxBerry::Web::lbfooter();

	exit;
}

