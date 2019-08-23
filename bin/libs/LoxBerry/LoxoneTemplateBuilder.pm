#!/usr/bin/perl
use warnings;
use strict;
use Carp;
use HTML::Entities;


package LoxBerry::LoxoneTemplateBuilder;

our $VERSION = "2.0.0.1";
our $DEBUG = 0;

if ($DEBUG) {
	print STDERR "LoxBerry::LoxoneTemplateBuilder: Developer warning - DEBUG mode is enabled in module\n" if ($DEBUG);
}

sub VirtualInHttp 
{

	my $class = shift;
	if (@_ % 2) {
		Carp::croak "Illegal parameter list has odd number of values\n" . join("\n", @_) . "\n";
	}
	my %params = @_;
	
	my $self = { 
				Title => $params{Title},
				Comment => $params{Comment} ? $params{Comment} : "",
				Address => $params{Address} ? $params{Address} : "",
				PollingTime => $params{append} ? $params{append} : "60",
				_type => 'VirtualInHttp'
	};
	
	bless $self, $class;

	$self->{VirtualInHttpCmd} = ( );
	
	return $self;

}

sub VirtualInHttpCmd
{
	my $self = shift;
	
	print STDERR "VirtualInHttpCmd: Number of parameters: " . @_ . "\n" if ($DEBUG);
	if(@_ == 1) {
		my $elementnr = shift;
		return $self->{VirtualInHttpCmd}[@$self->{VirtualInHttpCmd}-1];
	}
	
	if (@_ % 2) {
		Carp::croak "Illegal parameter list has odd number of values\n" . join("\n", @_) . "\n";
	}
	my %params = @_;

	my %VICmd = ( 
				_deleted => undef,
				Title => $params{Title},
				Comment => $params{Comment} ? $params{Comment} : "",
				Check => $params{Check} ? $params{Check} : "",
				Signed => ( defined $params{Signed} and !is_enabled($params{Signed}) ) ? "false" : "true",
				Analog => ( defined $params{Analog} and !is_enabled($params{Analog}) ) ? "false" : "true",
				SourceValLow => $params{SourceValLow} ? $params{SourceValLow} : "0",
				DestValLow => $params{DestValLow} ? $params{DestValLow} : "0",
				SourceValHigh => $params{SourceValHigh} ? $params{SourceValHigh} : "100",
				DestValHigh => $params{DestValHigh} ? $params{DestValHigh} : "100",
				DefVal => $params{DefVal} ? $params{DefVal} : "0",
				MinVal => $params{MinVal} ? $params{MinVal} : "-2147483647",
				MaxVal => $params{MaxVal} ? $params{MaxVal} : "2147483647"
	);

	push @{$self->{VirtualInHttpCmd}}, \%VICmd;

	return @{$self->{VirtualInHttpCmd}};

}

sub output
{
	my $self = shift;
	
	my $crlf = "\r\n";
	
	my $o;

	if($self->{_type} eq 'VirtualInHttp') {

		$o .= '<?xml version="1.0" encoding="utf-8"?>'.$crlf;

		$o .= '<VirtualInHttp ';
		$o .= 'Title="'.HTML::Entities::encode_entities($self->{Title}).'" ';
		$o .= 'Comment="'.HTML::Entities::encode_entities($self->{Comment}).'" ';
		$o .= 'Address="'.HTML::Entities::encode_entities($self->{Address}).'" ';
		$o .= 'PollingTime="'.$self->{PollingTime}.'"';
		$o .= '>'.$crlf;
		
		foreach my $VIcmd ( @{$self->{VirtualInHttpCmd}} ) {
			next if $VIcmd->{_deleted};
			
			$o .= "\t".'<VirtualInHttpCmd ';
			$o .= 'Title="'.HTML::Entities::encode_entities($VIcmd->{Title}).'" ';
			$o .= 'Comment="'.HTML::Entities::encode_entities($VIcmd->{Comment}).'" ';
			$o .= 'Check="'.HTML::Entities::encode_entities($VIcmd->{Check}).'" ';
			$o .= 'Signed="'.$VIcmd->{Signed}.'" ';
			$o .= 'Analog="'.$VIcmd->{Analog}.'" ';
			$o .= 'SourceValLow="'.$VIcmd->{SourceValLow}.'" ';
			$o .= 'DestValLow="'.$VIcmd->{DestValLow}.'" ';
			$o .= 'SourceValHigh="'.$VIcmd->{SourceValHigh}.'" ';
			$o .= 'DestValHigh="'.$VIcmd->{DestValHigh}.'" ';
			$o .= 'DefVal="'.$VIcmd->{Signed}.'" ';
			$o .= 'MinVal="'.$VIcmd->{Signed}.'" ';
			$o .= 'MaxVal="'.$VIcmd->{Signed}.'"';
			$o .= '/>'.$crlf;
		}
		
		$o .= '</VirtualInHttp>'.$crlf;
	}
	
	return $o;

}

sub delete 
{
	my $self = shift;
	
	if(@_ != 1) {
		Carp::croak "Delete needs exactly one parameter, the index of the element to delete";
	}
	
	if($self->{_type} eq 'VirtualInHttp') {
		
		my $elementnr = shift;
		$elementnr--;
		return 0 if ($elementnr < 0);

		if( defined $self->{VirtualInHttpCmd}[$elementnr] ) {
		
			$self->{VirtualInHttpCmd}[$elementnr]->{_deleted} = 1;
			return 1;
		}
	}
	
	return 0;
}






####################################################
# is_enabled - tries to detect if a string says 'True'
####################################################
sub is_enabled
{ 
	my ($text) = @_;
	$text =~ s/^\s+|\s+$//g;
	$text = lc $text;
	if ($text eq "true") { return 1;}
	if ($text eq "yes") { return 1;}
	if ($text eq "on") { return 1;}
	if ($text eq "enabled") { return 1;}
	if ($text eq "enable") { return 1;}
	if ($text eq "1") { return 1;}
	if ($text eq "check") { return 1;}
	if ($text eq "checked") { return 1;}
	if ($text eq "select") { return 1;}
	if ($text eq "selected") { return 1;}
	return undef;
}

#####################################################
# Finally 1; ########################################
#####################################################
1;
