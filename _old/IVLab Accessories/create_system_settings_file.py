import json
import os


#IV Lab settings
#"""
sp_wavelabs1 = dict(computer = dict(hardware = 'PC', os = 'Windows 10', basePath = r'D:\Data', sdPath = r'D:\IVlab\sd'),
                        IVsys = dict(sysName = 'IVLab', fullSunReferenceCurrent = 1.6, calibrationDateTime = 'Mon Jan 01 00:00:00 1900'),
                        lamp = dict(brand = 'Wavelabs', model = 'Sinus70'), 
                        SMU = dict(brand = 'Keithley', model = '2602', visa_address = 'GPIB0::24::INSTR', visa_library = 'C:\\Windows\\System32\\visa32.dll'))
#"""
#Ben's PC settings
"""
sp_wavelabs1 = dict(computer = dict(hardware = 'PC', os = 'Windows 10', basePath = "C:\\Users\\Public\\Documents\\IVLab", sdPath = "C:\\Users\\Public\\Documents\\IVLab\\sd"), 
                        IVsys = dict(sysName = 'IVLab', fullSunReferenceCurrent = 1.6, calibrationDateTime = 'Mon Jan 01 00:00:00 1900'),
                        lamp = dict(brand = 'Wavelabs', model = 'Sinus70'), 
                        SMU = dict(brand = 'Keithley', model = '2602', visa_address = 'GPIB0::24::INSTR', visa_library = 'C:\\Windows\\System32\\visa32.dll'))
"""
settingsFilePath = os.path.join(os.getcwd() , "system_settings.json")
with open(settingsFilePath, 'w') as outfile:
    json.dump(sp_wavelabs1, outfile)                        