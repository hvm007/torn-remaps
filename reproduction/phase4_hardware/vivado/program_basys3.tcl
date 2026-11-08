if {$argc != 1} {
  puts stderr "usage: program_basys3.tcl BITSTREAM"
  exit 2
}

set bitstream [lindex $argv 0]
if {![file isfile $bitstream]} {
  puts stderr "bitstream not found: $bitstream"
  exit 2
}

# Some Windows 2025.2 installations omit the nested appinit package directory
# after a local Tcl Store reset.  Hardware Manager requires that package, so
# fall back to the copy shipped with Vivado without installing or fetching
# anything.
if {[info exists ::env(XILINX_VIVADO)]} {
  set bundled_appinit [file join $::env(XILINX_VIVADO) data XilinxTclStore support appinit]
  if {[file isdirectory $bundled_appinit] && [lsearch -exact $::auto_path $bundled_appinit] == -1} {
    lappend ::auto_path $bundled_appinit
  }
  set bundled_apps [file join $::env(XILINX_VIVADO) data XilinxTclStore tclapp]
  foreach app_directory [glob -nocomplain -types d -directory $bundled_apps * *] {
    if {[lsearch -exact $::auto_path $app_directory] == -1} {
      lappend ::auto_path $app_directory
    }
  }
}

open_hw_manager
connect_hw_server
open_hw_target
set devices [get_hw_devices -quiet -filter {PART =~ "xc7a35t*"}]
if {[llength $devices] != 1} {
  puts stderr "expected one xc7a35t device, found [llength $devices]"
  close_hw_manager
  exit 3
}
set device [lindex $devices 0]
current_hw_device $device
refresh_hw_device $device
set_property PROGRAM.FILE $bitstream $device
program_hw_devices $device
refresh_hw_device $device
puts "NOC_TTV_BASYS3_PROGRAM_OK device=$device bitstream=$bitstream"
close_hw_manager
exit 0
