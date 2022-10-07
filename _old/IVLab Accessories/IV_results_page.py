import numpy as np
import matplotlib.pyplot as plt
import os
import datetime

v_smu = np.array([0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
i_smu = v_smu * 3.

IV_Params = {}
IV_Params['Imax'] = 0.005
IV_Params['Dwell'] = 5.0

IV_Results = {}
IV_Results['active_area'] = 0.16
IV_Results['cell_name'] = "Test Cell"
IV_Results['light_int'] = 100.
IV_Results['light_int_meas'] = 98.54
IV_Results['Voc'] = 1.0
IV_Results['Jsc'] = 2.0
IV_Results['Vmpp'] = 3.0
IV_Results['Jmpp'] = 4.0
IV_Results['Pmpp'] = 5.0
IV_Results['Pce'] = 6.0
IV_Results['FF'] = 7.0
IV_Results['start_V'] = v_smu[0]
IV_Results['stop_V'] = v_smu[len(v_smu)-1]
IV_Results['dV'] = 0.1
IV_Results['sweep_rate'] = 0.05
               
data_IV = {}
data_IV['scanType'] = 'JV'
data_IV['start_time'] = dateTimeString
data_IV['v'] = v_smu
data_IV['i'] = i_smu

lamp = {}
lamp['brand'] = 'Wavelabs'
lamp['model'] = 'sinus70'

dataFileName = "test_file_12345667.csv"

dateTimeString = datetime.datetime.now().strftime("%c") #"%Y%m%d_%H%M%S")

A4SizeY = 8.25 #inches, for A4
A4SizeX = 11.75 #inches, for A4

basepath, trash = os.path.split(os.getcwd())
logoPath = os.path.join(basepath,"IVLab Accessories","EPFL_Logo.png")
logo = plt.imread(logoPath)

#JV curve
fig = plt.figure(figsize=(A4SizeX,A4SizeY))
ax1 = fig.add_axes([0.5,0.5,0.4,0.4]) #x, y, width, height
ax1.invert_yaxis()
ax1.set_ylabel("current density [mA/$cm^2$]")
ax1.set_xlabel("voltage [V]")
ax1.grid(visible=True)
ax1.plot(v_smu, i_smu, color='red')

#report header - EPFL logo and cell name
ax2 = fig.add_axes([0.04,0.80,0.15,0.15])
ax2.axis('off')
ax2.imshow(logo)

#figtext is set relative to the figure.  'text' would be relative to an axis.
headerText = "Cell Name: " + IV_Results['cell_name'];
plt.figtext(0.20, 0.85, headerText, weight='bold', fontsize=15, ha='left') #, rotation=15, wrap=True)

#couldn't find a clean and simple way to print tabular text onto a figure that preserves all the spacings correctly.
#fill the data into a list of tuples with each tuple containing title, data, and unit strings.
#then print everything out with a specified spacing.

#coordinates of run param text columns
rpX1 = 0.05
rpX2 = 0.20
rpY = 0.8
rpSpace = 0.0225
params_text = []
params_text.append(("Measurement Date",dateTimeString, ""))
params_text.append(("Cell Active Area",str(IV_Results['active_area']),"$cm^2$"))
params_text.append(("Light Source",lamp['brand'] + " ",lamp['model']))
params_text.append(("Data File Name",dataFileName,""))
params_text.append(("Current Compliance",str(IV_Params['Imax']*1000.),"mA"))
params_text.append(("Settling Time",str(IV_Results['dV']/IV_Results['sweep_rate']),"s"))
params_text.append(("dV",str(IV_Results['dV']),"V"))
params_text.append(("Meas. Delay",str(IV_Params['Dwell']),"s"))
for label, data, units in params_text:
    plt.figtext(rpX1, rpY, label, fontsize=10, ha='left')
    plt.figtext(rpX2, rpY, ": " + data + units, fontsize=10, ha='left')
    rpY -= rpSpace


rtX1 = 0.05
rtX2 = 0.175
rtY = 0.55
rtSpace = 0.0225
results_text = []
results_text.append(("Light Intensity",str(IV_Results['light_int'])," mW/$cm^2$"))
if 'light_int_meas' in IV_Results:
    results_text.append(("Meas. Intensity",str(IV_Results['light_int_meas'])," mW/$cm^2$"))
if 'Jsc' in IV_Results:
    results_text.append(("Jsc",str(IV_Results['Jsc']), " mA/$cm^2$"))
if 'Voc' in IV_Results:
    results_text.append(("Voc",str(IV_Results['Voc']),"V"))
if 'Fill Factor' in IV_Results:
    results_text.append(("Fill Factor,",str(IV_Results['FF']),""))
if 'Pce' in IV_Results:
    results_text.append(("Pce",str(IV_Results['Pce']),"%"))
if 'Jmpp' in IV_Results:
    results_text.append(("Jmpp",str(IV_Results['Jmpp'])," mA/$cm^2$"))
if 'Vmpp' in IV_Results:
    results_text.append(("Vmpp",str(IV_Results['Vmpp']),"V"))
if 'Pmpp' in IV_Results:
    results_text.append(("Pmpp",str(IV_Results['Pmpp'])," mW/$cm^2$"))
    
for label, data, units in results_text:
    plt.figtext(rtX1, rtY, label, fontsize=10, ha='left')
    plt.figtext(rtX2, rtY, ": " + data + units, fontsize=10, ha='left')
    rtY -= rtSpace
    
username = 'jean toutlemonde'
systemName = 'IVLab'
#footer 1 - measured by
plt.figtext(0.05,0.05,"Measured by: " + username + " on " + systemName, fontsize = 10, ha = 'left')
plt.figtext(0.75,0.05,"Date: " + dateTimeString, fontsize = 10, ha = 'left')
    
plt.savefig("testFig.pdf")
plt.show()