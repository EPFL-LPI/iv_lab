from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedWidget,
    QWidget,
)

import pyqtgraph as pg


class GraphPanels(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Graph Widgets
        self.panelGraphIV = QWidget()
        self.panelGraphConstantV = QWidget()
        self.panelGraphConstantI = QWidget()
        self.panelGraphMPP = QWidget()
        self.panelGraphMPPIV = QWidget()
        self.panelGraphCalibration = QWidget()
        
        #IV plot widget and panel
        self.graphWidgetIV = pg.PlotWidget()
        #self.graphWidget.setMaximumWidth(2000) # does not appear to do anything
        #self.graphWidget.setMinimumSize(800,600)  # does not appear to do anything
        self.graphWidgetIV.setBackground('w')
        self.graphWidgetIV.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetIV.setLabel('left','Current (mA/cm^2)')
        self.graphWidgetIV.setLabel('bottom','Voltage (V)')
        self.curve_IV_valid = False
        #self.curve = self.graphWidget.plot([1,2,3],[1,2,3],pen=pg.mkPen('r', width=2))
        #self.graphWidget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        #pg.setConfigOption('foreground','r')
        
        #fields to give values computed from IV scan
        self.IVResultsWidget = QWidget()
        IVResultsLayout = QGridLayout()
        
        self.labelJsc = QLabel("Jsc:")
        self.fieldJsc = QLabel("-----")
        self.labelJscUnits = QLabel("mA/cm^2")
        
        self.labelVoc = QLabel("Voc:")
        self.fieldVoc = QLabel("-----")
        self.labelVocUnits = QLabel("V")
        
        self.labelFillFactor = QLabel("Fill Factor:")
        self.fieldFillFactor = QLabel("-----")
        self.labelFillFactorUnits = QLabel("")
        
        self.labelPce = QLabel("PCE:")
        self.fieldPce = QLabel("-----")
        self.labelPceUnits = QLabel("%")
        
        self.labelJmpp = QLabel("Jmpp:")
        self.fieldJmpp = QLabel("-----")
        self.labelJmppUnits = QLabel("mA/cm^2")
        
        self.labelVmpp = QLabel("Vmpp:")
        self.fieldVmpp = QLabel("-----")
        self.labelVmppUnits = QLabel("V")
        
        self.labelPmpp = QLabel("Pmpp:")
        self.fieldPmpp = QLabel("-----")
        self.labelPmppUnits = QLabel("mW/cm^2")
        
        IVResultsLayoutVoc = QHBoxLayout()
        IVResultsLayoutVoc.addWidget(self.labelVoc)
        IVResultsLayoutVoc.addWidget(self.fieldVoc)
        IVResultsLayoutVoc.addWidget(self.labelVocUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutVmpp = QHBoxLayout()
        IVResultsLayoutVmpp.addWidget(self.labelVmpp)
        IVResultsLayoutVmpp.addWidget(self.fieldVmpp)
        IVResultsLayoutVmpp.addWidget(self.labelVmppUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutPmpp = QHBoxLayout()
        IVResultsLayoutPmpp.addWidget(self.labelPmpp)
        IVResultsLayoutPmpp.addWidget(self.fieldPmpp)
        IVResultsLayoutPmpp.addWidget(self.labelPmppUnits)
        #IVResultsLayoutLine1.addStretch(1)
        IVResultsLayoutJsc = QHBoxLayout()
        IVResultsLayoutJsc.addWidget(self.labelJsc)
        IVResultsLayoutJsc.addWidget(self.fieldJsc)
        IVResultsLayoutJsc.addWidget(self.labelJscUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutPce = QHBoxLayout()
        IVResultsLayoutPce.addWidget(self.labelPce)
        IVResultsLayoutPce.addWidget(self.fieldPce)
        IVResultsLayoutPce.addWidget(self.labelPceUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutJmpp = QHBoxLayout()
        IVResultsLayoutJmpp.addWidget(self.labelJmpp)
        IVResultsLayoutJmpp.addWidget(self.fieldJmpp)
        IVResultsLayoutJmpp.addWidget(self.labelJmppUnits)
        #IVResultsLayoutLine2.addStretch(1)
        IVResultsLayoutFF = QHBoxLayout()
        IVResultsLayoutFF.addWidget(self.labelFillFactor)
        IVResultsLayoutFF.addWidget(self.fieldFillFactor)
        IVResultsLayoutFF.addWidget(self.labelFillFactorUnits)
        #IVResultsLayoutLine2.addStretch(1)
        
        IVResultsLayout.addLayout(IVResultsLayoutJsc,0,0)
        IVResultsLayout.addLayout(IVResultsLayoutVoc,1,0)
        IVResultsLayout.addLayout(IVResultsLayoutFF,2,0)
        IVResultsLayout.addLayout(IVResultsLayoutPce,3,0)
        IVResultsLayout.addLayout(IVResultsLayoutJmpp,0,2)
        IVResultsLayout.addLayout(IVResultsLayoutVmpp,1,2)
        IVResultsLayout.addLayout(IVResultsLayoutPmpp,2,2)
        IVResultsLayout.setColumnStretch(1,1)
        IVResultsLayout.setColumnStretch(3,1)
        #IVResultsLayout.setColumnStretch(5,1)
        
        self.IVResultsWidget.setLayout(IVResultsLayout)
        self.IVResultsWidget.setEnabled(False)

        panelGraphIVLayout = QVBoxLayout()
        panelGraphIVLayout.addWidget(self.graphWidgetIV)
        panelGraphIVLayout.addWidget(self.IVResultsWidget)
        self.panelGraphIV.setLayout(panelGraphIVLayout)
        
        self.addWidget(self.panelGraphIV)
        
        #Constant V plot widget and panel
        self.graphWidgetConstantV = pg.PlotWidget()
        self.graphWidgetConstantV.setBackground('w')
        self.graphWidgetConstantV.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetConstantV.setLabel('left','Current (mA/cm^2)')
        self.graphWidgetConstantV.setLabel('bottom','Time (sec)')
        self.curve_ConstantV_valid = False
        
        panelGraphConstantVLayout = QVBoxLayout()
        panelGraphConstantVLayout.addWidget(self.graphWidgetConstantV)
        self.panelGraphConstantV.setLayout(panelGraphConstantVLayout)
        
        self.addWidget(self.panelGraphConstantV)
        
        #Constant I plot widget and panel
        self.graphWidgetConstantI = pg.PlotWidget()
        self.graphWidgetConstantI.setBackground('w')
        self.graphWidgetConstantI.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetConstantI.setLabel('left','Voltage (V)')
        self.graphWidgetConstantI.setLabel('bottom','Time (sec)')
        self.curve_ConstantI_valid = False
        
        panelGraphConstantILayout = QVBoxLayout()
        panelGraphConstantILayout.addWidget(self.graphWidgetConstantI)
        self.panelGraphConstantI.setLayout(panelGraphConstantILayout)
        
        self.addWidget(self.panelGraphConstantI)
        
        #MPP plot widgets and panel
        self.graphWidgetMPP = pg.PlotWidget()
        self.graphWidgetMPP.setBackground('w')
        self.graphWidgetMPP.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetMPP.setLabel('left','Power (mW/cm^2)')
        self.graphWidgetMPP.setLabel('bottom','Time (sec)')
        self.curve_MPP_valid = False
        
        self.graphWidgetMPPIV = pg.PlotWidget()
        self.graphWidgetMPPIV.setBackground('w')
        #get the plotItem from the plotWidget
        self.plotItemMPPIV = self.graphWidgetMPPIV.plotItem
        self.plotItemMPPIV.setLabel('left','MPP Voltage (V)',color='#ff0000')
        self.plotItemMPPIV.showGrid(x = True, y = True, alpha = 0.3)
        self.plotItemMPPIV.setLabel('bottom','Time (sec)')
        self.plotItemMPPIV.setLabel('right','MPP Current (mA/cm^2)', color='#0000ff')
        self.curveMPPV = self.plotItemMPPIV.plot(x=[], y=[], pen=pg.mkPen('r', width=2))
   
        #create new viewbox to contain second plot, link it to the plot item, and add a curve to it
        self.viewBoxMPPI = pg.ViewBox()
        self.plotItemMPPIV.scene().addItem(self.viewBoxMPPI)
        self.plotItemMPPIV.getAxis('right').linkToView(self.viewBoxMPPI)
        self.viewBoxMPPI.setXLink(self.plotItemMPPIV)
        self.curveMPPI = pg.PlotCurveItem(pen=pg.mkPen('b', width=2))
        self.viewBoxMPPI.addItem(self.curveMPPI)
        #viewbox for 2nd curve needs to be told to track the size of the main plot on each change
        self.plotItemMPPIV.vb.sigResized.connect(self.updateViewsMPPIV)
        
        panelGraphMPPLayout = QVBoxLayout()
        panelGraphMPPLayout.addWidget(self.graphWidgetMPP)
        panelGraphMPPLayout.addWidget(self.graphWidgetMPPIV)
        self.panelGraphMPP.setLayout(panelGraphMPPLayout)
        
        self.addWidget(self.panelGraphMPP)
        
        #Calibration plot widgets and panel
        """self.graphWidgetCalibration = pg.PlotWidget()
        self.graphWidgetCalibration.setBackground('w')
        self.graphWidgetCalibration.showGrid(x = True, y = True, alpha = 0.3)
        self.graphWidgetCalibration.setLabel('left','Power (mW/cm^2)')
        self.graphWidgetCalibration.setLabel('bottom','Time (sec)')
        self.curve_Calibration_valid = False
        """
        self.graphWidgetCalibration = pg.PlotWidget()
        self.graphWidgetCalibration.setBackground('w')
        #get the plotItem from the plotWidget
        self.plotItemCalibration = self.graphWidgetCalibration.plotItem
        self.plotItemCalibration.setLabel('left','Calibration Diode Current (mA)',color='#ff0000')
        self.plotItemCalibration.showGrid(x = True, y = True, alpha = 0.3)
        self.plotItemCalibration.setLabel('bottom','Time (sec)')
        self.plotItemCalibration.setLabel('right','Reference Diode Current (mA)', color='#0000ff')
        self.curveCalibrationMeas = self.plotItemCalibration.plot(x=[], y=[], pen=pg.mkPen('r', width=2))
   
        #create new viewbox to contain second plot, link it to the plot item, and add a curve to it
        self.viewBoxCalibrationRef = pg.ViewBox()
        self.plotItemCalibration.scene().addItem(self.viewBoxCalibrationRef)
        self.plotItemCalibration.getAxis('right').linkToView(self.viewBoxCalibrationRef)
        self.viewBoxCalibrationRef.setXLink(self.plotItemCalibration)
        self.curveCalibrationRef = pg.PlotCurveItem(pen=pg.mkPen('b', width=2))
        self.viewBoxCalibrationRef.addItem(self.curveCalibrationRef)
        #viewbox for 2nd curve needs to be told to track the size of the main plot on each change
        self.plotItemCalibration.vb.sigResized.connect(self.updateViewsCalibration)
        
        panelGraphCalibrationLayout = QVBoxLayout()
        panelGraphCalibrationLayout.addWidget(self.graphWidgetCalibration)
        self.panelGraphCalibration.setLayout(panelGraphCalibrationLayout)
        
        self.addWidget(self.panelGraphCalibration)
    
    def updateViewsMPPIV(self):
        self.viewBoxMPPI.setGeometry(self.plotItemMPPIV.vb.sceneBoundingRect())
    
    def updateViewsCalibration(self):
        self.viewBoxCalibrationRef.setGeometry(self.plotItemCalibration.vb.sceneBoundingRect())
    
    def clearPlotIV(self):
        self.graphWidgetIV.clear()
        self.curve_IV_valid = False
    
    def clearPlotConstantV(self):
        self.graphWidgetConstantV.clear()
        self.curve_ConstantV_valid = False
    
    def clearPlotConstantI(self):
        self.graphWidgetConstantI.clear()
        self.curve_ConstantI_valid = False
    
    def clearPlotMPP(self):
        self.graphWidgetMPP.clear()
        self.curve_MPP_valid = False
    
    def clearPlotMPPIV(self):
        self.curveMPPV.setData(x=[], y=[])
        self.curveMPPI.setData(x=[], y=[])
    
    def clearPlotCalibration(self):
        self.curveCalibrationMeas.setData(x=[], y=[])
        self.curveCalibrationRef.setData(x=[], y=[])
