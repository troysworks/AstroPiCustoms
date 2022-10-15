# # from models import TrackerData
# # tracker_data = TrackerData()
# # from src.app import tracker_data
#
# temp_dec = 0
# temp_ra = 0
#
# def CM_sync():
#     print('')
#
#
# def get_mount_mode():
#     return 'P'  # testing.....
#     # if TrackerData.base.mount_select < 2:
#     #     return 'P'  # 0 = EQ 1 = Fork
#     # else:
#     #     return 'A'  # 2 = Alt Az
#
#
# # def move_mount(button, scale):
# #     if not TrackerData.base.soft_ra_adder:
# #         TrackerData.base.soft_ra_adder = 0
# #     if not TrackerData.base.soft_dec_adder:
# #         TrackerData.base.soft_dec_adder = 0
# #
# #     if button == 0:
# #         TrackerData.base.soft_ra_adder += scale / TrackerData.base.ra_or_az_pulse_per_deg
# #     elif button == 1:
# #         TrackerData.base.soft_ra_adder -= scale / TrackerData.base.ra_or_az_pulse_per_deg
# #     elif button == 2:
# #         TrackerData.base.soft_dec_adder += scale / TrackerData.base.dec_or_alt_pulse_per_deg
# #     elif button == 3:
# #         TrackerData.base.soft_dec_adder -= scale / TrackerData.base.dec_or_alt_pulse_per_deg
# #     return '0'
#
#
# # def move_to_new_location():
# #     TrackerData.base.ra_hour_decimal = temp_ra
# #     TrackerData.base.dec_deg_decimal = temp_dec
# #     TrackerData.base.control_mode = 2
# #     return '0'
#
#
# command_map = {
#     # Meade LX200 gps commands:
#     b'\x06': get_mount_mode,  # <0x06> Query of alignment mounting mode.Returns: A If scope in AltAz Mode L If scope in Land Mode P If scope in Polar Mode
#     '': get_mount_mode,  # <0x06> Query of alignment mounting mode.Returns: A If scope in AltAz Mode L If scope in Land Mode P If scope in Polar Mode
#     ':Gc#': '24#',  # Get Calendar Format Returns: 12# or 24#    #  Depending on the current telescope format setting.
#     ':GM#': 'Site1#',  # Get Site 1 Name Returns: <string>#    #  A ‘#’ terminated string with the name of the requested site.
#     ':GT#': tracker_data.base.ra_az_osc_calc,  # Get tracking rate Returns: TT.T#    # Current Track Frequency expressed in hertz assuming a synchonous motor design where a 60.0 Hz motor clock
#     # ':Gt#': TrackerData.base.latitude_dm,  # Get Current Site Latitude Returns: sDD*MM#     # The latitude of the current site. Positive inplies North latitude.
#     # ':GG#': TrackerData.base.utcoffset,  # Get UTC offset time Returns: sHH# or sHH.H#
#     # ':GL#': TrackerData.base.local_time,  # Get Local Time in 24 hour format Returns: HH:MM:SS#
#     # ':GC#': TrackerData.base.local_date,  # Get current date Returns: MM/DD/YY#    #  The current local calendar date for the telescope.
#     ':GVD#': '12 12 2022#',  # Get Telescope Firmware Date Returns: mmm dd yyyy#
#     ':GVT#': '01:01:01#',  # Get Telescope Firmware Time returns: HH:MM:SS#
#     ':GVN#': '41.0#',  # Get Telescope Firmware Number 'Version 4.2g' Returns: dd.d#
#     ':GVP#': 'AutostarMimic',  # Get Telescope Product Name Returns: <string>#
#     # ':CM': CM_sync,  # mybee with another drive mode or oneshot mode change
#     # ':GD': TrackerData.base.dec_deg_dms,  # Get Telescope Declination. Returns: sDD*MM# or sDD*MM’SS# Depending upon the current precision setting for the telescope.
#     # ':GR#': tracker_data.base.get_ra_hour_hms,  # Get Telescope RA Returns: HH:MM.T# or HH:MM:SS# Depending which precision is set for the telescope
#     # ':Me': return_none,  # start moving East at current slew rate
#     # ':Mn': return_none,  # start moving North at current slew rate
#     # ':Ms': return_none,  # start moving South at current slew rate
#     # ':Mw': return_none,  # start moving West at current slew rate
#     # ':MS': MS_move_to_target,  # after a pair of :Sr# and :Sd# commands. Slew to Target Object Returns:0 Slew is Possible 1<string># Object Below Horizon w/string message 2<string># Object Below Higher w/string message
#     # ':Q': return_none,  # abort all current slewing
#     # ':Qe': return_none,  # abort slew East
#     # ':Qn': return_none,  # abort slew North
#     # ':Qs': return_none,  # abort slew South
#     # ':Qw': return_none,  # abort slew West
#     # ':RC': return_none,  # set slew rate to centering (2nd slowest)
#     # ':RG': return_none,  # set slew rate to guiding (slowest)
#     # ':RM': return_none,  # set slew rate to find (2nd fastest)
#     # ':RS': return_none,  # set Slew rate to max (fastest)
#     # ':Sd': Sd_set_dec_deg('sDD*MM:SS'),  # Change to custom ra on form Sd +00:00:00#:MS#' Set target object declination to sDD*MM or sDD*MM:SS depending on the current precision setting
#     # ':Sr': Sr_set_ra_hr('HH:MM:SS'),  # Change to custom dec on form Set target object RA to HH:MM.T or HH:MM:SS depending on the current precision setting.
#     ':St': '1',  # St+39:44#' Sets the current site latitude to sDD*MM#
#     ':Sg': '1',  # Sg_set_longitude, # Sg104:59#' Set current site’s longitude to DDD*MM an ASCII position string
#     ':Sw': '1',  # set max slew rate Set maximum slew rate to N degrees per second. N is the range (2..8)Returns: 0 – Invalid 1 - Valid
#     ':SG': '1',  # SG_set_local_timezone, # :SGsHH.H# +06#' Set the number of hours added to local time to yield UTC 0 – Invalid 1 - Valid
#     ':SL': '1',  # SL_set_local_time, # :SLHH:MM:SS# Set the local Time Returns: 0 – Invalid 1 - Valid
#     ':SC': '1',  # SC_set_local_date, # :SCMM/DD/YY#  Change Handbox Date to MM/DD/YY  Returns: <D><string>  D = ‘0’ if the date is invalid. The string is the null string.
#     # ':hP#': TrackerData.base.control_mode = 3,  # Slew to park position Returns: nothing
#     # ':MA#': move_to_new_location(),  # :MA# Autostar, LX 16”, LX200GPS – Slew to target Alt and Az Returns: 0 - No fault 1 – Fault
#     # ':Me#': move_mount(1, .05),  # Move east (for equatorial mounts) or left (for altazimuth mounts) at current rate.  # Returns: nothing
#     # ':Mn#': move_mount(2, .05)  # Move north (for equatorial mounts) or up (for altazimuth mounts) at current rate.    # Returns: nothing
#     # ':Ms#' move_mount(3, .05)  # Move south (for equatorial mounts) or down (for altazimuth mounts) at current rate.    # Returns: nothing
#     # ':Mw#': move_mount(0, .05)  # Move west (for equatorial mounts) or right (for altazimuth mounts) at current rate.    # Returns: nothing
#     # ':MgeXXXX#': guide_mount(1, xxx=ms),  # :MeXXX# Corrects the position of the mount to the east (for equatorial mounts) or left (for altazimuth mounts) by an amount equivalent to a motion of XXX milliseconds at the
#     # ':MgnXXXX#': guide_mount(2, xxx=ms),  # :MnXXX# Corrects the position of the mount to the north (for equatorial mounts) or up (for altazimuth mounts) by an amount equivalent to a motion of XXX milliseconds at the
#     # ':MgsXXXX#': guide_mount(3, xxx=ms),  # :MsXXX# Corrects the position of the mount to the south (for equatorial mounts) or down (for altazimuth mounts) by an amount equivalent to a motion of XXX milliseconds at the
#     # ':MgwXXXX#': guide_mount(0, xxx=ms)  # :MwXXX# Corrects the position of the mount to the west (for equatorial mounts) or right (for altazimuth mounts) by an amount equivalent to a motion of XXX milliseconds at the
# }
